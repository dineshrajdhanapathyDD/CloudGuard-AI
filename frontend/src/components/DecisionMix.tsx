import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import type { Stats } from "./StatCards";

export function DecisionMix({ stats }: { stats: Stats }) {
  const data = [
    { name: "Proceed", value: stats.proceed, fill: "#34d399" },
    { name: "Clarify", value: stats.clarify, fill: "#fbbf24" },
    { name: "Deny", value: stats.deny, fill: "#f87171" },
  ].filter((d) => d.value > 0);

  if (stats.total === 0) return null;

  return (
    <div className="flex items-center gap-4 rounded-xl border border-line bg-panel/70 p-4">
      <div className="h-24 w-24 shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" innerRadius={28} outerRadius={46} paddingAngle={2} stroke="none">
              {data.map((d, i) => (
                <Cell key={i} fill={d.fill} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div>
        <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-mute">Decision mix</div>
        <ul className="space-y-0.5 font-mono text-xs">
          <li className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-sm bg-proceed" /> Proceed {stats.proceed}
          </li>
          <li className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-sm bg-clarify" /> Clarify {stats.clarify}
          </li>
          <li className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-sm bg-deny" /> Deny {stats.deny}
          </li>
        </ul>
      </div>
    </div>
  );
}
