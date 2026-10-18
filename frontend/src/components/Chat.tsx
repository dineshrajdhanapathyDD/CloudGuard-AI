import { useEffect, useRef, useState } from "react";
import { Send, User, Bot } from "lucide-react";

export interface ChatMsg {
  role: "user" | "bot";
  text: string;
  meta?: string;
}

export function Chat({
  messages,
  busy,
  onSend,
}: {
  messages: ChatMsg[];
  busy: boolean;
  onSend: (text: string) => void;
}) {
  const [input, setInput] = useState("");
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const t = input.trim();
    if (!t || busy) return;
    setInput("");
    onSend(t);
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div ref={logRef} className="flex-1 space-y-3 overflow-auto pr-1">
        {messages.length === 0 && (
          <p className="mt-8 text-center text-sm text-mute">
            Ask CloudGuard to investigate an AWS resource, or run a scenario above.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-2.5 ${m.role === "user" ? "flex-row-reverse" : ""}`}>
            <span
              className={`mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg ${
                m.role === "user" ? "bg-cyan/15 text-cyan" : "bg-orange/15 text-orange"
              }`}
            >
              {m.role === "user" ? <User size={15} /> : <Bot size={15} />}
            </span>
            <div
              className={`max-w-[85%] rounded-2xl border px-3.5 py-2.5 text-sm leading-relaxed ${
                m.role === "user" ? "border-cyan/30 bg-cyan/5" : "border-line bg-panel2"
              }`}
            >
              <p className="whitespace-pre-wrap">{m.text}</p>
              {m.meta && <p className="mt-1.5 font-mono text-[11px] text-mute">{m.meta}</p>}
            </div>
          </div>
        ))}
        {busy && (
          <div className="flex gap-2.5">
            <span className="mt-0.5 grid h-7 w-7 place-items-center rounded-lg bg-orange/15 text-orange">
              <Bot size={15} />
            </span>
            <div className="rounded-2xl border border-line bg-panel2 px-3.5 py-2.5 text-sm text-mute">
              <span className="animate-pulseline">Evaluating with the decision gate...</span>
            </div>
          </div>
        )}
      </div>

      <form onSubmit={submit} className="mt-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={busy}
          placeholder="Investigate i-1234567890abcdef0..."
          aria-label="Message CloudGuard AI"
          className="flex-1 rounded-xl border border-line bg-panel2 px-4 py-3 text-sm outline-none placeholder:text-mute/70 focus:border-cyan/60 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="inline-flex items-center gap-2 rounded-xl bg-cyan px-4 font-semibold text-bg transition hover:bg-cyan/90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Send size={16} /> Send
        </button>
      </form>
    </div>
  );
}
