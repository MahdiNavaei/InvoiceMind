Param(
    [string]$OutDir = "data/raw/Arshasb"
)

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$url = 'https://drive.google.com/uc?export=download&id=1G9JEZY9MSzaND8ynnFodIXQvMMM1_6J3'
$outfile = Join-Path $OutDir 'Arshasb_7k.tar.gz'

Write-Host "Downloading Arshasb sample to $outfile"
Invoke-WebRequest -Uri $url -OutFile $outfile
Write-Host "Download complete. Extract and inspect with tar / 7zip."
