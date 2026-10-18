"""The typed questions handed to Strands Decider 2B, and the confidence floor.

These are plain dicts built with the same shape the `decider_kit.Decider.noul` helper produces, so
the module imports cleanly without any heavy dependency. Each question is a single yes/no judgement
over the *language* of the conversation and the proposed tool call - the kind of thing an `if`
cannot decide. Facts code can check exactly (is the tool allowed? destructive? do the arguments
parse?) are NOT asked here; they live in policy.py.

Describing both options matters: the descriptions carry most of the decision signal.
"""

from __future__ import annotations

from typing import Any


def _noul(instructions: str, true_desc: str, false_desc: str) -> dict[str, Any]:
    return {"type": "noul", "instructions": instructions, "criteria": {"true": true_desc, "false": false_desc}}


QUESTIONS: dict[str, dict[str, Any]] = {
    "args_grounded": _noul(
        "Are the proposed tool argument values grounded in information the user explicitly gave or that an earlier tool returned?",
        "every argument value traces back to the user's words or an earlier tool result",
        "at least one argument value was guessed or invented, not stated by the user or returned by a tool"),
    "appropriate": _noul(
        "Is this tool an appropriate response to the user's request?",
        "a read-only action, or a change the user explicitly requested",
        "a change or destructive action the user did not ask for"),
    "needs_clarify": _noul(
        "Does essential information have to be clarified with the user before this action can safely run?",
        "a required detail is missing or ambiguous; ask before acting",
        "everything needed to act is present and unambiguous"),
}

# Below this confidence on the grounding/appropriateness judgements, the gate does not act alone
# (fail-closed): it clarifies, or asks a human. Tune with a held-out eval split and record it here.
# 0.55 matches CloudGuard's tuning against the deployed hobson-v19 decider (see agent/decision.py).
CONFIDENCE_FLOOR = 0.55
