import type { ChatResponse, Info } from "../types";

// Calls go to /api/* (same-origin in dev via the Vite proxy -> the FastAPI demo server on 8501,
// and same-origin in production if the built dist/ is served by that server).

export async function getInfo(): Promise<Info> {
  const r = await fetch("/api/info");
  if (!r.ok) throw new Error(`info failed: ${r.status}`);
  return r.json();
}

export async function sendChat(message: string, sessionId = "dashboard"): Promise<ChatResponse> {
  const r = await fetch("/api/chat", {
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
  await fetch("/api/reset", { method: "POST" });
}
