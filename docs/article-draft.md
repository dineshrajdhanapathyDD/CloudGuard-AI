# CloudGuard AI: a decision gate that stops an AWS agent from acting on thin air

> Draft for an AWS Builder Center article. Tags: `strands-decider-2b`, `guardrails`.
>
> Every measured number below is a PLACEHOLDER marked `<<from a real run>>`. Fill them from
> `evaluation/results.json` (run with `--decider real`) and `submission/bench/results.json`
> (`./kit bench --split test`) before publishing. Do not invent numbers. The kit's `/write-article`
> skill and `./kit article` build the paste-ready bundle with the real figures and charts.

## The problem

An AWS operations agent is useful right up until it is dangerous. Ask it to look into high CPU and
it reads a metric — fine. Ask it something vague and an eager model will happily invent an instance
id, call a tool, and report confident nonsense. Worse, nudge it toward "fix the server" and it may
reach for a restart or a terminate nobody approved. The generative model is good at language and
bad at restraint.

CloudGuard AI puts a **decision gate** in front of every tool call. Amazon Bedrock still does the
talking and the tool use. But before a tool runs, Strands Decider 2B makes one constrained
judgement, and a deterministic policy — not the model — decides whether the call proceeds, needs
clarification, or is blocked.

## What the agent does

A short real exchange (from a `--decider real` run; replace with your own transcript):

- "Investigate high CPU on i-1234567890abcdef0." → grounded, read-only → **PROCEED**, metrics come
  back.
- "Check why my EC2 CPU is high." → no instance named → **CLARIFY**: which instance?
- "The server is slow, just terminate it." → destructive, unrequested → **DENY**.
- "Fix the production server." → ambiguous remediation → **DENY / CLARIFY**, never an automatic
  restart.

## The decision handed to Strands Decider 2B

Three narrow yes/no questions, asked about one state in a single forward pass:

```python
QUESTIONS = {
  "args_grounded": noul("Are the proposed tool argument values grounded in information the user "
                        "explicitly gave or that an earlier tool returned?", ...),
  "appropriate":   noul("Is this tool an appropriate response to what the user actually asked "
                        "for, given the evidence so far?", ...),
  "needs_clarify": noul("Does essential information have to be clarified with the user before "
                        "this action can safely run?", ...),
}
```

The model only classifies. Everything an `if` can decide exactly — is the tool permitted? is it
destructive? does the instance id parse? — stays in code (`agent/policy.py`) and feeds a
deterministic, fail-closed policy. Hard rules are checked first, so the LLM can never talk the gate
into an unsafe action; a destructive or unknown tool is denied before the model is even consulted.
A legitimate request with a fabricated argument CLARIFIES (asks the user) rather than hard-denying;
an inappropriate or destructive action DENIES. Uncertainty — low confidence, a malformed answer, or
a decider that is down — never PROCEEDs.

## Wiring

The gate is a Strands `InterventionHandler` (`agent/decision.py`):

```python
agent = Agent(model=agent_model(), tools=TOOLS,
              interventions=[AWSOperationGuard(Decider())])
```

`before_tool_call` runs the three questions and the policy, then returns `Proceed`, `Guide`
(CLARIFY), `Deny`, or `Confirm`. A guided call retried unchanged is denied, so the loop converges.
The same pattern is packaged standalone in `decision_patterns/guardrail_gate/` with its own README
and tests, so another builder can lift it in a few minutes.

## Measured

Fill from real runs before publishing:

- Guardrail decision accuracy: `<<from a real run>>` (end-to-end, `evaluation/results.json`).
- False-allow rate on unsafe/ungrounded calls: `<<from a real run>>`.
- False-deny rate on legitimate calls: `<<from a real run>>`.
- Decider latency p50 / p95: `<<from a real run>>`.
- Decider vs. Amazon Bedrock LLM on the same questions (accuracy, latency, cost per 1,000):
  `<<from ./kit bench --split test>>`.
- Decider model, mode, and hardware: `<<state exactly what ran>>`.

Be honest about weak spots: name the question the decider confuses most, and what you tried.

## What I learned

- Separate "classify" from "decide". The model's calibrated probabilities are an input; the
  branch lives in code I can read, test and audit.
- Fail-closed beats clever. The most valuable rules are the boring ones: unknown tool → deny,
  decider down → do not run.
- Grounding failures are usually a missing detail, not malice — clarifying keeps the agent useful
  while staying safe.

## Footer

Built by Dineshraj Dhanapathy via AWSUGMDU.

The reusable `decider_kit/` library, the demo UI and the tooling are by the **AWS User Group
Madurai**. Built with the AWS User Group Madurai Strands Decider hackathon kit.
