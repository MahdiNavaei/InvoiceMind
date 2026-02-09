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

type ActionRequest = {
  action?: "cancel" | "replay";
};

export async function POST(req: NextRequest, { params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  const body = (await req.json().catch(() => ({}))) as ActionRequest;
  const action = body.action;
  if (action !== "cancel" && action !== "replay") {
    return NextResponse.json({ error: "action must be cancel or replay" }, { status: 400 });
  }

  const token = await getToken();
  if (!token) {
    return NextResponse.json({ error: "cannot acquire backend token" }, { status: 500 });
  }

  const backendRes = await fetch(`${apiBaseUrl()}/v1/runs/${encodeURIComponent(runId)}/${action}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Accept-Language": "en-US"
    },
    cache: "no-store"
  });

  const payload = (await backendRes.json().catch(() => ({ error: "invalid backend response" }))) as Record<string, unknown>;
  return NextResponse.json(payload, { status: backendRes.status });
}
