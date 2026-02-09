$ErrorActionPreference = "Stop"

function Wait-HttpReady {
  param(
    [Parameter(Mandatory = $true)][string]$Url,
    [int]$MaxAttempts = 60,
    [int]$DelayMs = 1000
  )
  for ($i = 0; $i -lt $MaxAttempts; $i++) {
    try {
      $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
      if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
        return $true
      }
    } catch {
      Start-Sleep -Milliseconds $DelayMs
    }
  }
  return $false
}

function New-ValidPngBytes {
  $tmpPath = [System.IO.Path]::ChangeExtension([System.IO.Path]::GetTempFileName(), ".png")
  $py = @"
from PIL import Image
img = Image.new("RGB", (1024, 1024), (255, 255, 255))
img.save(r"$tmpPath", format="PNG")
"@
  $py | python -
  $bytes = [System.IO.File]::ReadAllBytes($tmpPath)
  Remove-Item -Path $tmpPath -Force -ErrorAction SilentlyContinue
  return $bytes
}

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$frontendDir = Join-Path $root "frontend"

$backendProc = $null
$frontendProc = $null
$frontendLog = [System.IO.Path]::GetTempFileName()

try {
  Write-Host "Starting backend on http://127.0.0.1:8000 ..."
  $backendProc = Start-Process -FilePath "python" -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") -WorkingDirectory $root -PassThru -WindowStyle Hidden
  if (-not (Wait-HttpReady -Url "http://127.0.0.1:8000/health")) {
    throw "Backend did not become ready in time."
  }

  $healthEn = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Headers @{ "Accept-Language" = "en-US" }
  $healthFa = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Headers @{ "Accept-Language" = "fa-IR" }

  $tokenResp = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/v1/auth/token" -ContentType "application/json" -Body '{"username":"admin","password":"admin123"}'
  $adminToken = $tokenResp.access_token
  $adminHeaders = @{ "Authorization" = "Bearer $adminToken" }

  $payload = New-ValidPngBytes
  $payloadFile = [System.IO.Path]::ChangeExtension([System.IO.Path]::GetTempFileName(), ".png")
  [System.IO.File]::WriteAllBytes($payloadFile, $payload)
  $upload = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/v1/documents" -Headers @{
    "Authorization" = "Bearer $adminToken"
    "X-Filename" = "smoke_invoice.png"
    "X-Content-Type" = "image/png"
  } -ContentType "application/octet-stream" -InFile $payloadFile
  Remove-Item -Path $payloadFile -Force -ErrorAction SilentlyContinue

  if ($upload.ingestion_status -ne "ACCEPTED") {
    $reasons = ""
    if ($upload.quarantine_reason_codes) {
      $reasons = ($upload.quarantine_reason_codes -join ",")
    }
    throw "Upload did not pass contract validation. ingestion_status=$($upload.ingestion_status); reasons=$reasons"
  }

  $run = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/v1/documents/$($upload.id)/runs" -Headers $adminHeaders
  $runId = $run.run_id

  $terminal = @("SUCCESS", "WARN", "NEEDS_REVIEW", "FAILED", "CANCELLED")
  $runState = $null
  for ($i = 0; $i -lt 80; $i++) {
    $runState = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/v1/runs/$runId" -Headers $adminHeaders
    if ($terminal -contains $runState.status) {
      break
    }
    Start-Sleep -Milliseconds 500
  }
  if (-not ($terminal -contains $runState.status)) {
    throw "Run did not reach terminal state in time."
  }

  $auditorTokenResp = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/v1/auth/token" -ContentType "application/json" -Body '{"username":"auditor","password":"audit123"}'
  $auditorToken = $auditorTokenResp.access_token
  $auditorHeaders = @{ "Authorization" = "Bearer $auditorToken" }

  $export = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/v1/runs/$runId/export" -Headers $auditorHeaders
  $auditVerify = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/v1/audit/verify" -Headers $auditorHeaders

  Write-Host "Starting frontend on http://127.0.0.1:3000 ..."
  $frontendCmd = "npm run start -- --hostname 127.0.0.1 --port 3000 > `"$frontendLog`" 2>&1"
  $frontendProc = Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $frontendCmd) -WorkingDirectory $frontendDir -PassThru -WindowStyle Hidden
  if (-not (Wait-HttpReady -Url "http://127.0.0.1:3000/" -MaxAttempts 120 -DelayMs 1000)) {
    $frontendTail = (Get-Content -Path $frontendLog -ErrorAction SilentlyContinue | Select-Object -Last 40) -join "`n"
    throw "Frontend did not become ready in time.`n$frontendTail"
  }

  $frontRoot = Invoke-WebRequest -Uri "http://127.0.0.1:3000/" -UseBasicParsing
  $frontFa = Invoke-WebRequest -Uri "http://127.0.0.1:3000/fa/dashboard" -UseBasicParsing
  $frontEn = Invoke-WebRequest -Uri "http://127.0.0.1:3000/en/dashboard" -UseBasicParsing

  $summary = [ordered]@{
    timestamp_utc = [DateTime]::UtcNow.ToString("o")
    backend = [ordered]@{
      health_en = $healthEn.message
      health_fa = $healthFa.message
      upload_ingestion_status = $upload.ingestion_status
      run_id = $runId
      run_status = $runState.status
      run_review_decision = $runState.review_decision
      audit_chain_valid = $auditVerify.valid
      export_status = $export.status
    }
    frontend = [ordered]@{
      root_status_code = $frontRoot.StatusCode
      fa_dashboard_status_code = $frontFa.StatusCode
      en_dashboard_status_code = $frontEn.StatusCode
    }
  }

  $json = ($summary | ConvertTo-Json -Depth 6)
  Write-Host $json
} finally {
  if ($frontendProc -and -not $frontendProc.HasExited) {
    Stop-Process -Id $frontendProc.Id -Force
  }
  if ($frontendLog -and (Test-Path $frontendLog)) {
    Remove-Item -Path $frontendLog -Force -ErrorAction SilentlyContinue
  }
  if ($backendProc -and -not $backendProc.HasExited) {
    Stop-Process -Id $backendProc.Id -Force
  }
}
