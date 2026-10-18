import { useEffect, useRef, useState } from "react";
import { Header } from "./components/Header";
import { StatCards, computeStats } from "./components/StatCards";
import { DecisionMix } from "./components/DecisionMix";
import { ScenarioLauncher } from "./components/ScenarioLauncher";
import { DecisionCard } from "./components/DecisionCard";
import { Chat, type ChatMsg } from "./components/Chat";
import { getInfo, sendChat } from "./services/api";
import type { DecisionRecord, Info } from "./types";

export default function App() {
  const [info, setInfo] = useState<Info | null>(null);
  const [infoError, setInfoError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [decisions, setDecisions] = useState<DecisionRecord[]>([]);
  const [busy, setBusy] = useState(false);
  const decRef = useRef<HTMLDivElement>(null);
  // A fresh session per page load, so the agent re-investigates each request and the gate fires
  // every time (a warm, reused session lets the LLM answer from context without new tool calls,
  // which would show "0 decisions"). A new scenario from the launcher also gets a fresh session.
  const sessionRef = useRef(`dash-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`);

  useEffect(() => {
    getInfo()
      .then(setInfo)
      .catch((e) => setInfoError(String(e)));
  }, []);

  useEffect(() => {
    decRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  }, [decisions]);

  async function run(message: string, fresh = false) {
    if (busy) return;
    setBusy(true);
    // Scenarios are independent demos: start each in a new session so the gate always fires.
    if (fresh) sessionRef.current = `dash-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
    setMessages((m) => [...m, { role: "user", text: message }]);
    try {
      const out = await sendChat(message, sessionRef.current);
      const n = out.decisions.length;
      setMessages((m) => [
        ...m,
        {
          role: "bot",
          text: out.reply,
          meta: `${out.latency_ms} ms · ${n} decision${n === 1 ? "" : "s"}${out.served_by ? " · " + out.served_by : ""}`,
        },
      ]);
      if (n) setDecisions((d) => [...out.decisions.slice().reverse(), ...d]);
    } catch (e) {
      setMessages((m) => [...m, { role: "bot", text: `Error: ${String(e)}` }]);
    } finally {
      setBusy(false);
      // Signal turn completion for the kit's video recorder (make_video.py waits on this), matching
      // the old static UI's contract.
      document.body.dataset.turns = String((Number(document.body.dataset.turns) || 0) + 1);
    }
  }

  const stats = computeStats(decisions);

  return (
    <div className="flex h-full flex-col">
      <Header info={info} />

      {infoError && (
        <div className="border-b border-deny/40 bg-deny/10 px-6 py-2 text-xs text-deny">
          Cannot reach the CloudGuard API ({infoError}). Start the backend: <span className="font-mono">kit.cmd demo-bg</span>{" "}
          (or <span className="font-mono">python -m uvicorn demo.server:app --port 8501</span>), then reload.
        </div>
      )}

      <main className="grid min-h-0 flex-1 gap-5 p-5 lg:grid-cols-[1.15fr_1fr]">
        {/* Left column: overview + scenarios + chat */}
        <section className="flex min-h-0 flex-col gap-4">
          <StatCards stats={stats} />
          <DecisionMix stats={stats} />
          <ScenarioLauncher onRun={(m) => run(m, true)} busy={busy} />
          <div className="flex min-h-0 flex-1 flex-col rounded-2xl border border-line bg-panel/70 p-4">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-mute">Conversation</h2>
            <Chat messages={messages} busy={busy} onSend={run} />
          </div>
        </section>

        {/* Right column: live decision stream */}
        <section className="flex min-h-0 flex-col rounded-2xl border border-line bg-panel/70 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-mute">Strands Decider 2B decisions</h2>
            {decisions.length > 0 && (
              <button
                onClick={() => setDecisions([])}
                className="text-[11px] text-mute hover:text-ink hover:underline"
              >
                clear
              </button>
            )}
          </div>
          <div ref={decRef} className="min-h-0 flex-1 space-y-3 overflow-auto pr-1">
            {decisions.length === 0 ? (
              <p className="mt-8 text-center text-sm text-mute">
                Decisions appear here as the gate evaluates each proposed AWS tool call.
              </p>
            ) : (
              decisions.map((d, i) => <DecisionCard key={decisions.length - i} rec={d} />)
            )}
          </div>
        </section>
      </main>

      <footer className="border-t border-line px-6 py-3 text-center text-[11px] text-mute">
        Built by Dineshraj Dhanapathy via AWSUGMDU (Agent Experience Hackathon)
      </footer>
    </div>
  );
}
