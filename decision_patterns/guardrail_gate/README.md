# guardrail_gate — a reusable Strands Decider 2B decision gate for tool calls

`#guardrails`

A small, self-contained pattern that puts **Strands Decider 2B** in front of an agent's tool
calls. Before any guarded tool runs, the gate asks the decider three narrow, language-level
questions, combines the answers with facts your code already knows, and returns one of
**PROCEED / CLARIFY / DENY**. The generative model (Amazon Bedrock) does the talking and the tool
use; the decider makes the one constrained judgement that keeps it safe.

This is the decision pattern behind **CloudGuard AI** (see `agent/decision.py` and
`agent/policy.py` in this repo). It is duplicated here, dependency-light, so you can read and lift
it on its own.

## What it does

Agents go wrong in predictable ways: they invent missing arguments, reach for the wrong tool, or
act before they have enough information. Three things need *reading the conversation* to catch —
exactly what an `if` statement cannot do, and exactly what a 2B decision model does well in one
calibrated forward pass:

1. **args_grounded** — do the argument values trace back to what the user actually said (or an
   earlier tool result), or were they fabricated?
2. **appropriate** — is this tool a sensible response to the request and the evidence so far?
3. **needs_clarify** — is essential information missing, so the agent should ask first?

Everything the model should *not* be trusted with stays in code: whether the tool is even
permitted, whether it is destructive, and whether its arguments are structurally valid. Those
facts are computed in `policy.py` and fed to the decision alongside the decider's probabilities.

## Typed questions and options

```python
from decision_patterns.guardrail_gate import QUESTIONS
# QUESTIONS = {
#   "args_grounded": noul("...grounded in what the user gave...", true=..., false=...),
#   "appropriate":   noul("...appropriate for the request...",    true=..., false=...),
#   "needs_clarify": noul("...must be clarified before running...", true=..., false=...),
# }
```

Each is a yes/no (`noul`) question with **both** options described — the descriptions carry most
of the signal. Ask all three about one state in a single `Decider.ask(...)` call: the state is
encoded once and shared.

## The policy (deterministic, fail-closed)

`decide(PolicyInput, probs, confidence)` returns `PolicyOutcome(action, reason, confirmable)`.
Hard rules are checked **first**, so the LLM can never talk the gate into an unsafe action:

| Condition (checked in order) | Action |
|---|---|
| tool is destructive | **DENY** |
| tool is not allowed | **DENY** |
| arguments fail structural validation | **CLARIFY** |
| `appropriate` below `yes` (wrong action for the request) | **DENY** |
| `args_grounded` below `yes` (value fabricated/missing) | **CLARIFY** |
| confidence below `confidence_floor` (default 0.60) | **CLARIFY** (human-confirmable) |
| `needs_clarify` at/above `yes` | **CLARIFY** |
| otherwise | **PROCEED** |

A **DENY** is reserved for actions that are wrong to take at all (destructive, unpermitted, or
inappropriate). A legitimate request whose argument was fabricated or is missing **CLARIFIES** so
the user can supply it. Both are fail-closed: the action does not run.

**Fail-closed** means uncertainty never PROCEEDs: a destructive or unknown tool, invalid
arguments, a decider that errors or times out, or a sub-threshold confidence all stop the action.
The decider's confidence is never the only control.

## Wiring

```python
from decider_kit import Decider
from decision_patterns.guardrail_gate import GuardrailGate
from strands import Agent

gate = GuardrailGate(
    Decider(),
    guarded={"get_ec2_metrics", "terminate_ec2_instance"},   # tools to inspect
    allowed={"get_ec2_metrics"},                              # tools permitted at all
    destructive={"terminate_ec2_instance"},                  # never executed
    validate=my_validate,          # (tool, args) -> (ok: bool, error: str | None)
)
agent = Agent(model=..., tools=[...], interventions=[gate])
```

`GuardrailGate` is a `strands.interventions.InterventionHandler`:
- `before_tool_call` runs the gate and returns `Proceed`, `Guide` (CLARIFY → the agent asks the
  user), `Deny`, or `Confirm` (human approval, with `confirm_when_unsure=True`);
- `before_invocation` resets per-turn state so a previously-guided call can be retried once the
  user supplies the missing detail;
- a guided call retried **unchanged** is denied (Strands requires `Guide` handlers to converge).

Every verdict is appended to `gate.log` for your demo UI, audit trail and benchmark.

## How to reuse it

1. Copy this folder into your project.
2. Fill the three sets (`guarded`, `allowed`, `destructive`) and a `validate(tool, args)` callable
   for your tools.
3. Reword the three `QUESTIONS` for your domain if needed — keep one judgement per question and
   describe both options.
4. Tune `yes` and `confidence_floor` on a held-out eval split (`./kit bench`) and record the
   values you chose.

## Tests

```bash
.venv/Scripts/python.exe -m pytest decision_patterns/guardrail_gate/tests -q   # Windows
.venv/bin/python -m pytest decision_patterns/guardrail_gate/tests -q           # macOS / Linux
```

`test_policy.py` covers every policy branch with no decider or network; `test_handler.py` drives
the Strands wiring with a fake decider, including the destructive-tool block and Guide→Deny
convergence.

---

Built by Dineshraj Dhanapathy via AWSUGMDU (Agent Experience Hackathon).
