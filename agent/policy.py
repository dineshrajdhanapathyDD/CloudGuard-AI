"""Deterministic, fail-closed safety policy for CloudGuard AI.

The Strands Decider 2B gate (decision.py) hands this module three probabilities (grounding,
appropriateness, need-to-clarify) together with facts that code - not a model - owns: whether the
tool is permitted, whether it is destructive, and whether its arguments pass structural
validation. This module combines them into exactly one action:

    PROCEED  - the call is permitted, grounded, appropriate, and nothing needs clarifying;
    CLARIFY  - a required argument is missing/fabricated, essential information is missing,
               confidence is too low, or structural validation failed - ask the user, do not act;
    DENY     - the tool is not allowed or is destructive, or the decider judged the action itself
               inappropriate for the request.

Fail-closed means: anything the policy is not sure is safe does NOT PROCEED. A destructive tool,
an unknown tool, malformed arguments, a decider that errored, or a sub-threshold confidence can
never yield PROCEED. The generative LLM cannot override a DENY - it only ever sees the refusal.
A DENY is reserved for actions that are wrong to take at all (destructive, unpermitted, or
inappropriate); a legitimate request with a missing or fabricated argument CLARIFIES instead, so
the user can supply the detail.

These are policy choices, not claims about the model's built-in behaviour. Thresholds live here in
code so they are auditable and tunable (see CONFIDENCE_FLOOR and ./kit bench).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# --- Tool catalogue: the code-owned facts the decider never sees --------------------------------

# Every tool CloudGuard is permitted to use at all. Fail-closed: a tool not in this set is denied,
# even if the LLM proposes it and the decider likes it.
ALLOWED_TOOLS = {
    "get_ec2_instance_details",
    "get_ec2_metrics",
    "get_cloudwatch_alarms",
    "summarize_investigation",
}

# Destructive / irreversible actions. The MVP never executes these; they exist so the gate can
# demonstrably DENY an unrequested destructive action (hackathon scenario 3) and refuse to
# auto-run a restart (scenario 4). They are intentionally NOT in ALLOWED_TOOLS.
DESTRUCTIVE_TOOLS = {
    "terminate_ec2_instance",
    "restart_ec2_instance",
    "delete_cloudwatch_alarm",
    "stop_ec2_instance",
}

# Which tool calls the guardrail inspects. Read-only tools are still checked for grounding; the
# gate runs on all AWS tools so fabricated identifiers are caught even on read-only calls.
GUARDED_TOOLS = ALLOWED_TOOLS | DESTRUCTIVE_TOOLS

# Metric names the read-only metrics tool accepts (structural validation, done in code).
VALID_METRICS = {
    "CPUUtilization",
    "NetworkIn",
    "NetworkOut",
    "DiskReadBytes",
    "DiskWriteBytes",
    "StatusCheckFailed",
}

# An EC2 instance id: "i-" then 8 or 17 hex characters.
INSTANCE_ID_RE = re.compile(r"^i-[0-9a-f]{8}(?:[0-9a-f]{9})?$")


@dataclass
class Validation:
    ok: bool
    error: str | None = None


def validate_arguments(tool: str, args: dict[str, Any]) -> Validation:
    """Structural checks an `if` can do exactly - never asked of the decider.

    Validates the *shape* of arguments (is this a well-formed instance id? a known metric?). It
    does NOT judge whether the values are grounded in the conversation - that is the decider's job.
    """
    if tool in ("get_ec2_instance_details", "get_ec2_metrics", "restart_ec2_instance",
                "terminate_ec2_instance", "stop_ec2_instance"):
        instance_id = str(args.get("instance_id", "")).strip()
        if not instance_id:
            return Validation(False, "no instance_id was provided")
        if not INSTANCE_ID_RE.match(instance_id):
            return Validation(False, f"'{instance_id}' is not a well-formed EC2 instance id")
    if tool == "get_ec2_metrics":
        metric = str(args.get("metric", "")).strip()
        if metric and metric not in VALID_METRICS:
            return Validation(False, f"'{metric}' is not a supported metric")
    return Validation(True)


# --- The policy ---------------------------------------------------------------------------------

@dataclass
class PolicyInput:
    tool: str
    args: dict[str, Any]
    allowed: bool          # tool in ALLOWED_TOOLS (code)
    destructive: bool      # tool in DESTRUCTIVE_TOOLS (code)
    args_valid: bool       # validate_arguments(...).ok (code)
    validation_error: str | None = None


@dataclass
class PolicyOutcome:
    action: str            # "PROCEED" | "CLARIFY" | "DENY"
    reason: str
    confirmable: bool = False  # a CLARIFY that a human could approve instead (restart, etc.)


def decide(
    pin: PolicyInput,
    probs: dict[str, float],
    confidence: float,
    *,
    yes: float = 0.5,
    confidence_floor: float = 0.60,
) -> PolicyOutcome:
    """Combine code-owned facts with the decider's probabilities into one fail-closed action.

    Order matters: deterministic DENY rules are checked first so the generative model can never
    talk the gate into running an unsafe action. Only when every hard rule passes do the decider's
    language judgements decide between PROCEED and CLARIFY.
    """
    grounded = probs.get("args_grounded", 0.0)
    appropriate = probs.get("appropriate", 0.0)
    needs_clarify = probs.get("needs_clarify", 0.0)

    # 1. Hard, code-owned DENY rules (the model cannot override these).
    if pin.destructive:
        return PolicyOutcome(
            "DENY",
            f"'{pin.tool}' is a destructive action. CloudGuard does not execute destructive AWS "
            "operations; it investigates. If you need this done, it must go through a human-approved change.",
        )
    if not pin.allowed:
        return PolicyOutcome(
            "DENY",
            f"'{pin.tool}' is not a permitted CloudGuard tool, so the request is blocked.",
        )
    if not pin.args_valid:
        return PolicyOutcome(
            "CLARIFY",
            f"The arguments are not usable: {pin.validation_error}. Ask the user for a valid value instead of guessing.",
        )

    # 2. Appropriateness is a DENY: an inappropriate tool (e.g. a remediation when the user only
    #    asked to investigate) does not get a second chance by clarifying - it is the wrong action.
    if appropriate < yes:
        return PolicyOutcome(
            "DENY",
            "This action is not an appropriate response to the request. Blocking it.",
        )

    # 3. Ungrounded arguments are a CLARIFY, not a DENY: the request itself is legitimate, but a
    #    required value was fabricated or is missing, so we ask the user instead of guessing or
    #    acting. (Fail-closed either way: the action does not run.) This matches hackathon
    #    scenario 2 - a missing instance id means "ask which instance", not a hard refusal.
    if grounded < yes:
        return PolicyOutcome(
            "CLARIFY",
            "The arguments are not grounded in anything the user said or a verified source; they "
            "look fabricated. Ask the user which resource to investigate before running this.",
        )

    # 4. Fail-closed on uncertainty: not confident enough to act alone -> clarify (or human confirm).
    if confidence < confidence_floor:
        return PolicyOutcome(
            "CLARIFY",
            f"Confidence ({confidence:.2f}) is below the floor ({confidence_floor:.2f}); confirming before acting.",
            confirmable=True,
        )

    # 5. The decider says essential information is still missing.
    if needs_clarify >= yes:
        return PolicyOutcome(
            "CLARIFY",
            "Essential information is missing or ambiguous. Ask the user to clarify before running this action.",
        )

    # 6. Permitted, grounded, appropriate, confident, nothing to clarify.
    return PolicyOutcome("PROCEED", "Grounded, appropriate, and sufficiently certain to run.")
