import { Activity, CheckCircle2, HelpCircle, ShieldX, Timer } from "lucide-react";
import type { DecisionRecord } from "../types";

export interface Stats {
  total: number;
  proceed: number;
  clarify: number;
  deny: number;
  avgLatency: number | null;
}

export function computeStats(decisions: DecisionRecord[]): Stats {
  const total = decisions.length;
  const proceed = decisions.filter((d) => d.verdict === "proceed").length;
  const clarify = decisions.filter((d) => d.verdict === "clarify" || d.verdict === "confirm").length;
  const deny = decisions.filter((d) => d.verdict === "deny").length;
  const lat = decisions.map((d) => d.decider_ms).filter((m) => m > 0);
  const avgLatency = lat.length ? Math.round(lat.reduce((a, b) => a + b, 0) / lat.length) : null;
  return { total, proceed, clarify, deny, avgLatency };
}

function Card({
  icon,
  label,
  value,
  accent,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  accent: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-line bg-panel/70 px-4 py-3">
      <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-lg ${accent}`}>{icon}</span>
      <div className="min-w-0">
        <div className="truncate text-[11px] uppercase tracking-wider text-mute">{label}</div>
        <div className="font-mono text-xl font-semibold">{value}</div>
      </div>
    </div>
  );
}

export function StatCards({ stats }: { stats: Stats }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
      <Card icon={<Activity size={18} />} label="Evaluated" value={String(stats.total)} accent="bg-cyan/15 text-cyan" />
      <Card icon={<CheckCircle2 size={18} />} label="Proceed" value={String(stats.proceed)} accent="bg-proceed/15 text-proceed" />
      <Card icon={<HelpCircle size={18} />} label="Clarify" value={String(stats.clarify)} accent="bg-clarify/15 text-clarify" />
      <Card icon={<ShieldX size={18} />} label="Deny" value={String(stats.deny)} accent="bg-deny/15 text-deny" />
      <Card
        icon={<Timer size={18} />}
        label="Avg decider"
        value={stats.avgLatency === null ? "-" : `${stats.avgLatency} ms`}
        accent="bg-orange/15 text-orange"
      />
    </div>
  );
}
