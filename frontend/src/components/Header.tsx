import { ShieldCheck, Cloud, Cpu, Radio } from "lucide-react";
import type { Info } from "../types";

function deciderLabel(decider: string): string {
  if (decider === "ugmdu") return "Strands Decider 2B (AWS UG hosted)";
  if (decider === "local") return "Strands Decider 2B (local)";
  if (decider === "custom") return "Strands Decider 2B (self-hosted)";
  return `Strands Decider (${decider})`;
}

export function Header({ info }: { info: Info | null }) {
  const live = info?.target === "agentcore";
  return (
    <header className="flex flex-wrap items-center gap-x-5 gap-y-2 border-b border-line px-6 py-4">
      <div className="flex items-center gap-3">
        <span className="grid h-9 w-9 place-items-center rounded-xl bg-cyan/15 text-cyan">
          <ShieldCheck size={20} />
        </span>
        <div>
          <h1 className="text-lg font-extrabold tracking-tight">CloudGuard AI</h1>
          <p className="text-xs text-mute">The decision gate for AWS operations</p>
        </div>
      </div>

      <div className="ml-auto flex flex-wrap items-center gap-2 text-xs">
        <span
          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 font-mono ${
            live ? "border-proceed/50 text-proceed" : "border-clarify/50 text-clarify"
          }`}
          title={live ? "Answered by the deployed agent on AWS" : "Answered by a local agent"}
        >
          <Radio size={13} className={live ? "animate-pulseline" : ""} />
          {live ? "LIVE · AgentCore Runtime" : "LOCAL agent"}
        </span>
        {info && (
          <>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-line px-3 py-1 font-mono text-mute">
              <Cloud size={13} className="text-orange" />
              {info.llm}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-line px-3 py-1 font-mono text-mute">
              <Cpu size={13} className="text-cyan" />
              {deciderLabel(info.decider)}
            </span>
          </>
        )}
      </div>
    </header>
  );
}
