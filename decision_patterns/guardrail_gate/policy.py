"""The deterministic, fail-closed policy.

Takes the three Decider probabilities plus code-owned facts and returns exactly one action:
PROCEED / CLARIFY / DENY. Hard DENY rules are checked first, so a generative model can never talk
the gate into running an unsafe or unrequested action. Only when every hard rule passes do the
model's language judgements decide between PROCEED and CLARIFY. Fail-closed: a destructive or
unknown tool, invalid arguments, an unavailable decider, or sub-threshold confidence never
PROCEEDs.

This module has no third-party dependencies and no I/O, so it is trivial to unit-test in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PolicyInput:
    tool: str
    args: dict[str, Any]
    allowed: bool          # is the tool permitted at all? (code)
    destructive: bool      # is the tool irreversible/destructive? (code)
    args_valid: bool       # did structural validation pass? (code)
    validation_error: str | None = None


@dataclass
class PolicyOutcome:
    action: str            # "PROCEED" | "CLARIFY" | "DENY"
    reason: str
    confirmable: bool = False  # a CLARIFY a human could approve instead


def decide(
    pin: PolicyInput,
    probs: dict[str, float],
    confidence: float,
    *,
    yes: float = 0.5,
    confidence_floor: float = 0.60,
) -> PolicyOutcome:
    grounded = probs.get("args_grounded", 0.0)
    appropriate = probs.get("appropriate", 0.0)
    needs_clarify = probs.get("needs_clarify", 0.0)

    # 1. Hard, code-owned DENY rules (the model cannot override these).
    if pin.destructive:
        return PolicyOutcome("DENY", f"'{pin.tool}' is destructive; this gate never executes destructive operations.")
    if not pin.allowed:
        return PolicyOutcome("DENY", f"'{pin.tool}' is not a permitted tool, so the request is blocked.")
    if not pin.args_valid:
        return PolicyOutcome("CLARIFY", f"Arguments are not usable: {pin.validation_error}. Ask for a valid value.")

    # 2. An inappropriate action is the wrong action - DENY (no second chance by clarifying).
    if appropriate < yes:
        return PolicyOutcome("DENY", "This action is not an appropriate response to the request.")

    # 3. Ungrounded arguments: the request is legitimate but a value was fabricated/missing -
    #    CLARIFY (ask the user), not DENY. Fail-closed either way: the action does not run.
    if grounded < yes:
        return PolicyOutcome("CLARIFY", "Arguments are not grounded in anything the user said; ask which resource to use.")

    # 4. Fail-closed on uncertainty.
    if confidence < confidence_floor:
        return PolicyOutcome("CLARIFY", f"Confidence {confidence:.2f} is below the floor {confidence_floor:.2f}; confirm first.", confirmable=True)

    # 5. The decider says essential information is still missing.
    if needs_clarify >= yes:
        return PolicyOutcome("CLARIFY", "Essential information is missing or ambiguous; clarify before acting.")

    # 6. Permitted, grounded, appropriate, confident, nothing to clarify.
    return PolicyOutcome("PROCEED", "Grounded, appropriate and sufficiently certain to run.")
