import { Play } from "lucide-react";
import { SCENARIOS } from "../scenarios";
import { VERDICT_META } from "./verdict";

export function ScenarioLauncher({
  onRun,
  busy,
}: {
  onRun: (message: string) => void;
  busy: boolean;
}) {
  return (
    <div className="rounded-2xl border border-line bg-panel/70 p-4">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-mute">Run a scenario</h2>
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {SCENARIOS.map((s) => {
          const meta = VERDICT_META[s.expected];
          return (
            <button
              key={s.id}
              onClick={() => onRun(s.message)}
              disabled={busy}
              title={s.note}
              className="group flex flex-col gap-1 rounded-xl border border-line bg-panel2 p-3 text-left transition hover:border-cyan/50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-semibold">{s.title}</span>
                <span className={`rounded-full border px-2 py-0.5 font-mono text-[10px] ${meta.border} ${meta.color}`}>
                  {meta.label}
                </span>
              </div>
              <span className="line-clamp-2 text-xs text-mute">{s.message}</span>
              <span className="mt-1 inline-flex items-center gap-1 text-[11px] font-medium text-cyan opacity-0 transition group-hover:opacity-100">
                <Play size={11} /> Run
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
