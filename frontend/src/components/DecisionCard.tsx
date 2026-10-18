import { useState } from "react";
import { ChevronDown, Wrench, Clock, AlertTriangle, CheckCircle2 } from "lucide-react";
import type { DecisionRecord } from "../types";
import { VERDICT_META, barColor } from "./verdict";

function ProbBar({ name, value }: { name: string; value: number | undefined }) {
  if (value === undefined) return null;
  return (
    <div className="grid grid-cols-[120px_1fr_40px] items-center gap-2 font-mono text-xs">
      <span className="text-mute">{name}</span>
      <span className="h-2.5 overflow-hidden rounded-full bg-line/60">
        <span className="block h-full rounded-full" style={{ width: `${value * 100}%`, background: barColor(value) }} />
      </span>
      <span className="text-right">{value.toFixed(2)}</span>
    </div>
  );
}

export function DecisionCard({ rec }: { rec: DecisionRecord }) {
  const [open, setOpen] = useState(false);
  const meta = VERDICT_META[rec.verdict] ?? VERDICT_META.deny;
  const hasProbs = rec.args_grounded !== undefined;

  return (
    <div className={`animate-pop rounded-xl border bg-panel2 p-3.5 ${meta.border}`}>
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="inline-flex items-center gap-2 text-sm font-semibold">
          <Wrench size={14} className="text-mute" />
          <span className="font-mono">{rec.tool}</span>
        </span>
        <span className={`rounded-full border px-2.5 py-0.5 font-mono text-[11px] font-bold ${meta.border} ${meta.color} ${meta.bg}`}>
          {meta.label}
        </span>
      </div>

      {hasProbs ? (
        <div className="space-y-1.5">
          <ProbBar name="args_grounded" value={rec.args_grounded} />
          <ProbBar name="appropriate" value={rec.appropriate} />
          <ProbBar name="needs_clarify" value={rec.needs_clarify} />
        </div>
      ) : (
        <p className="font-mono text-[11px] text-mute">Blocked in code before the model was consulted (fail-closed).</p>
      )}

      <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[11px] text-mute">
        <span className="inline-flex items-center gap-1">
          <span className="text-ink">conf</span> {rec.confidence.toFixed(2)}
        </span>
        <span className="inline-flex items-center gap-1">
          <Clock size={11} /> {rec.decider_ms} ms
        </span>
        <span className="inline-flex items-center gap-1">
          {rec.decider_ok ? <CheckCircle2 size={11} className="text-proceed" /> : <AlertTriangle size={11} className="text-deny" />}
          decider {rec.decider_ok ? "ok" : "down"}
        </span>
        <span className="inline-flex items-center gap-1">
          {rec.args_valid ? <CheckCircle2 size={11} className="text-proceed" /> : <AlertTriangle size={11} className="text-clarify" />}
          args {rec.args_valid ? "valid" : "invalid"}
        </span>
      </div>

      <p className="mt-2 text-xs leading-relaxed text-ink/90">{rec.reason}</p>

      <button
        onClick={() => setOpen((o) => !o)}
        className="mt-2 inline-flex items-center gap-1 text-[11px] font-medium text-cyan hover:underline"
        aria-expanded={open}
      >
        <ChevronDown size={12} className={`transition ${open ? "rotate-180" : ""}`} />
        {open ? "Hide" : "Show"} audit trace
      </button>
      {open && (
        <pre className="mt-2 overflow-auto rounded-lg border border-line bg-bg/60 p-2.5 font-mono text-[10.5px] leading-relaxed text-mute">
          {JSON.stringify(rec, null, 2)}
        </pre>
      )}
    </div>
  );
}
