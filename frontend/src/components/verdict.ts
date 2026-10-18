import type { Verdict } from "../types";

export const VERDICT_META: Record<Verdict, { label: string; color: string; bg: string; border: string }> = {
  proceed: { label: "PROCEED", color: "text-proceed", bg: "bg-proceed/10", border: "border-proceed/50" },
  clarify: { label: "CLARIFY", color: "text-clarify", bg: "bg-clarify/10", border: "border-clarify/50" },
  confirm: { label: "CONFIRM", color: "text-cyan", bg: "bg-cyan/10", border: "border-cyan/50" },
  deny: { label: "DENY", color: "text-deny", bg: "bg-deny/10", border: "border-deny/50" },
};

export function barColor(v: number): string {
  return v >= 0.5 ? "#34d399" : "#f87171";
}
