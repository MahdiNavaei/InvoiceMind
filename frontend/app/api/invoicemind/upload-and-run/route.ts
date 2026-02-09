import { NextRequest, NextResponse } from "next/server";

function apiBaseUrl(): string {
  return process.env.INVOICEMIND_API_BASE_URL || "http://localhost:8000";
}

async function getToken(): Promise<string | null> {
  const staticToken = process.env.INVOICEMIND_API_TOKEN;
  if (staticToken) return staticToken;

  const username = process.env.INVOICEMIND_API_USERNAME || "admin";
  const password = process.env.INVOICEMIND_API_PASSWORD || "admin123";
  try {
    const res = await fetch(`${apiBaseUrl()}/v1/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept-Language": "en-US" },
      body: JSON.stringify({ username, password }),
      cache: "no-store"
    });
    if (!res.ok) return null;
    const payload = (await res.json()) as { access_token?: string };
    return payload.access_token || null;
  } catch {
    return null;
  }
}

export async function POST(req: NextRequest) {
  const form = await req.formData();
  const file = form.get("file");
  const autoRun = String(form.get("auto_run") || "true") !== "false";

  if (!(file instanceof File)) {
    return NextResponse.json({ error: "file is required" }, { status: 400 });
  }

  const token = await getToken();
  if (!token) {
    return NextResponse.json({ error: "cannot acquire backend token" }, { status: 500 });
  }

  const filename = file.name || "upload.bin";
  const contentType = file.type || "application/octet-stream";
  const payload = Buffer.from(await file.arrayBuffer());

  const uploadRes = await fetch(`${apiBaseUrl()}/v1/documents`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Filename": filename,
      "X-Content-Type": contentType,
      "Content-Type": "application/octet-stream"
    },
    body: payload,
    cache: "no-store"
  });
  const uploadBody = (await uploadRes.json()) as Record<string, unknown>;

  let runBody: Record<string, unknown> | null = null;
  if (uploadRes.ok && autoRun && uploadBody.ingestion_status === "ACCEPTED" && typeof uploadBody.id === "string") {
    const runRes = await fetch(`${apiBaseUrl()}/v1/documents/${encodeURIComponent(uploadBody.id)}/runs`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store"
    });
    runBody = (await runRes.json()) as Record<string, unknown>;
  }

  return NextResponse.json(
    {
      upload: uploadBody,
      run: runBody
    },
    { status: uploadRes.ok ? 200 : uploadRes.status }
  );
}
