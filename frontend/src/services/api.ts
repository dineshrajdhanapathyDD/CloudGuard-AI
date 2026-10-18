import type { ChatResponse, Info } from "../types";

// API base:
//   - unset (local dev / served by the demo server): relative /api/* (Vite proxy or same origin).
//   - set to the deployed API URL (Amplify build): absolute calls to the Lambda/API Gateway.
// Set at build time with VITE_API_BASE, e.g. VITE_API_BASE=https://abc.execute-api.us-east-1.amazonaws.com
const BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");

export async function getInfo(): Promise<Info> {
  const r = await fetch(`${BASE}/api/info`);
  if (!r.ok) throw new Error(`info failed: ${r.status}`);
  return r.json();
}

export async function sendChat(message: string, sessionId = "dashboard"): Promise<ChatResponse> {
  const r = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  const data = (await r.json()) as ChatResponse;
  if (!r.ok || data.error) {
    throw new Error(data.error ?? `chat failed: ${r.status}`);
  }
  return data;
}

export async function resetSession(): Promise<void> {
  await fetch(`${BASE}/api/reset`, { method: "POST" });
}
