# CloudGuard AI — architecture

CloudGuard AI is an AWS operations assistant with a **decision gate**. Amazon Bedrock handles the
generative work (understanding the request, choosing a tool, writing the explanation). Strands
Decider 2B handles one constrained judgement before any tool runs: is the proposed call grounded,
appropriate, and does anything need clarifying? A deterministic, fail-closed policy turns that
judgement — plus facts the code owns — into PROCEED, CLARIFY, or DENY.

## Request flow

```
            user request
                 |
                 v
     +-----------------------------+
     |  HackathonAgent.chat()      |   agent/agent.py
     |  Strands Agent + Amazon     |
     |  Bedrock (Nova Pro)         |
     +-------------+---------------+
                   | proposes a tool call
                   v
     +-----------------------------+
     |  AWSOperationGuard          |   agent/decision.py
     |  (Strands InterventionHandler,
     |   before_tool_call)         |
     +-------------+---------------+
                   |
      1. code-owned facts (no model):
         allowed? destructive? args valid?   agent/policy.py
                   |
         hard DENY (destructive / unknown) -> stop here, no model call
                   |
      2. Strands Decider 2B, one forward pass:
         args_grounded? appropriate? needs_clarify?   decider_kit/client.py
                   |
      3. deterministic fail-closed policy -> PROCEED | CLARIFY | DENY   agent/policy.py
                   |
      +------------+-------------+-------------------+
      |            |             |                   |
   PROCEED      CLARIFY        DENY            (decider error)
      |         (Guide:        (Deny:          -> treated as
      v          ask user)     refuse)            CLARIFY/DENY,
  tool runs        |             |                never PROCEED
 (simulated,       v             v
  read-only)   back to LLM   refusal to LLM
      |         to ask            |
      v             +-------------+
  Amazon Bedrock writes the human-readable reply
      |
      v
  UI: decision, confidence, latency, tool result, full audit trace
```

## Components (kept separate)

| Concern | Where |
|---|---|
| Agent orchestration (Bedrock + tools) | `agent/agent.py` (`HackathonAgent`) |
| Decider inference adapter | `decider_kit/client.py` (`Decider`) — one client for a local server or the hosted API |
| Guardrail intervention handler | `agent/decision.py` (`AWSOperationGuard`, a Strands `InterventionHandler`) |
| Deterministic safety policy | `agent/policy.py` (`decide`, `validate_arguments`, tool catalogue) |
| Tool registry and executor | `agent/tools.py` (four simulated read-only AWS tools) |
| Audit event service | `AWSOperationGuard.log` — one structured record per decision |
| API layer | `demo/server.py` (FastAPI) |
| Frontend | `demo/static/index.html` (chat + live decision panel) |
| Reusable pattern (standalone) | `decision_patterns/guardrail_gate/` |

## The one decision (`#guardrails`)

Three narrow yes/no questions, asked about one state in a single forward pass
(`agent/decision.py:QUESTIONS`):

- **args_grounded** — do the argument values trace back to what the user said or an earlier tool
  result, or were they invented?
- **appropriate** — is this tool the right response to the request and the evidence?
- **needs_clarify** — is essential information missing, so the agent should ask first?

The model only classifies. Everything an `if` can decide exactly — is the tool permitted? is it
destructive? does the instance id parse? — is computed in `agent/policy.py` and fed to the policy
alongside the probabilities. Thresholds (`yes = 0.5`, `confidence_floor = 0.60`) live in code.

## Fail-closed policy

Order matters: hard DENY rules are checked first so the generative model can never talk the gate
into an unsafe action.

1. destructive tool → **DENY**
2. tool not permitted → **DENY**
3. arguments fail structural validation → **CLARIFY**
4. `appropriate` below threshold (wrong action) → **DENY**
5. `args_grounded` below threshold (fabricated/missing value) → **CLARIFY** (ask the user)
6. confidence below the floor → **CLARIFY** (optionally a human `Confirm`)
7. `needs_clarify` at/above threshold → **CLARIFY**
8. otherwise → **PROCEED**

A decider that is unavailable, returns malformed output, or is not confident enough never yields
PROCEED. The decider's confidence is never the only control.

## Why a decision model, not an LLM, for the gate

Grounding, appropriateness and "is something missing" need *reading the conversation* — judgements
an `if` cannot make. A 2B decision model answers all three in one calibrated forward pass and
returns a number the policy branches on, which is faster, cheaper and more private than a second
generative LLM call, and gives a confidence the code can act on. See `evaluation/` for the measured
comparison.

## Deployment

`./kit deploy` packages the agent for Amazon Bedrock AgentCore Runtime (see `deploy/agentcore/`).
The deployed agent always uses Amazon Bedrock for the generative part and the hosted Strands
Decider 2B for the decision. Tools are simulated read-only stubs in the MVP; optional live boto3
read-only adapters activate only with `CLOUDGUARD_LIVE_AWS=1`.

Built by Dineshraj Dhanapathy via AWSUGMDU.

Built with the AWS User Group Madurai Strands Decider hackathon kit.
