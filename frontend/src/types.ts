// Types mirror the CloudGuard demo server contract (demo/server.py) and the agent's decision
// record shape (agent/decision.py: AWSOperationGuard._record). Verified against a live deployed
// invoke, so these match what AgentCore Runtime returns.

export type Verdict = "proceed" | "clarify" | "deny" | "confirm";

export interface DecisionRecord {
  pattern: string; // "#guardrails"
  tool: string;
  args: Record<string, unknown>;
  verdict: Verdict;
  reason: string;
  confidence: number; // 0..1
  args_valid: boolean;
  decider_ok: boolean;
  decider_ms: number;
  // The three typed Decider 2B probabilities (0..1). Absent on hard code-owned denials.
  args_grounded?: number;
  appropriate?: number;
  needs_clarify?: number;
}

export interface ChatResponse {
  reply: string;
  decisions: DecisionRecord[];
  model_id: string;
  latency_ms: number;
  agent: string;
  eager: boolean;
  served_by?: string; // present when answered by the deployed AgentCore runtime
  error?: string;
}

export interface Info {
  agent: string;
  llm: string;
  bedrock_model: string;
  decider: string; // "ugmdu" | "local" | "custom"
  target: string; // "agentcore" | "local"
}

export interface Scenario {
  id: string;
  title: string;
  message: string;
  expected: Verdict;
  note: string;
}
