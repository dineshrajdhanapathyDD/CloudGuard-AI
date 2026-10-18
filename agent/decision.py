"""REUSABLE DECISION PATTERN: aws-operation guardrail gate  (#guardrails)

What it does
    CloudGuard AI is an AWS operations assistant. Before it runs any AWS tool, this gate hands
    Strands Decider 2B the conversation plus the proposed tool call and asks three narrow,
    language-level judgements:
      - args_grounded:  do the argument values (instance ids, metric names, ...) trace back to
                        what the user actually said or to an earlier verified tool result, or
                        were they invented?
      - appropriate:    is this tool a sensible response to what the user asked for, given the
                        evidence so far?
      - needs_clarify:  is essential information missing, so the agent should ask the user
                        before acting?
    The model only classifies. A deterministic policy (see `policy.py`) combines those three
    probabilities with code-owned facts the decider never sees - whether the tool is even
    permitted, whether it is destructive, and whether the arguments pass structural validation -
    and returns one of PROCEED / CLARIFY / DENY. The policy is fail-closed: a destructive or
    unknown tool, malformed arguments, or a decider that is unavailable or unsure never results
    in the action running.

Typed questions and options
    args_grounded (noul), appropriate (noul), needs_clarify (noul); see QUESTIONS below.

Wiring (where it sits in the agent's path)
    `AWSOperationGuard` is a Strands `InterventionHandler`. agent/agent.py passes it to the Agent:

        Agent(..., interventions=[AWSOperationGuard(Decider())])

    The framework calls `before_tool_call` before every tool runs. Read-only, grounded calls
    PROCEED; a DENY is returned to the model as a hard refusal (Strands `Deny`); a CLARIFY is
    returned as `Guide` so the agent asks the user instead of guessing. If the agent retries the
    exact same guided call unchanged, the retry is denied (Strands requires Guide to converge).
    `before_invocation` clears the per-turn guided set.

How to reuse it
    Copy this file into your own agent. Then:
      1. list your irreversible/destructive tools in DESTRUCTIVE_TOOLS and the tools the agent is
         allowed to use at all in ALLOWED_TOOLS (fail-closed: anything else is denied);
      2. reword the three QUESTIONS for your domain (keep one judgement per question, and
         describe both options - the descriptions carry most of the signal);
      3. keep the facts code already knows (permission, risk, structural validation) in
         `policy.py` and out of the decider;
      4. tune thresholds with `./kit bench` and record the chosen values in `policy.py`.
    Nothing here depends on CloudGuard's tools; the gate is the reusable piece.

This gate is also packaged standalone under `decision_patterns/guardrail_gate/` with its own
README and tests, so another builder can read it without the rest of the app.
"""

from __future__ import annotations

import json
from typing import Any

from strands.interventions import Confirm, Deny, Guide, InterventionHandler, Proceed

from decider_kit import Decider, DeciderError
from decider_kit.patterns.guardrails import render_messages

from .policy import (
    ALLOWED_TOOLS,
    DESTRUCTIVE_TOOLS,
    GUARDED_TOOLS,
    PolicyInput,
    decide,
    validate_arguments,
)

PATTERN_TAG = "#guardrails"

# The three language-level judgements handed to Strands Decider 2B. Facts code can check exactly
# (is the tool allowed? is it destructive? do the arguments parse?) are NOT here - they live in
# policy.py, computed in code, and fed to the policy alongside these probabilities.
QUESTIONS = {
    "args_grounded": Decider.noul(
        "Does every argument value in the proposed tool call appear in the conversation above - stated by the user or returned by an earlier tool?",
        {"true": "each argument value (for example the instance id) is present verbatim in the user's messages or an earlier tool result",
         "false": "at least one argument value does not appear anywhere in the conversation; it was guessed or invented"}),
    "appropriate": Decider.noul(
        "Is this tool an appropriate response to the user's request?",
        {"true": "a read-only investigation (reading instance details, metrics or alarms), or a change the user explicitly asked for",
         "false": "a change or destructive action (restart, stop, terminate, delete) the user did not ask for"}),
    "needs_clarify": Decider.noul(
        "Does essential information have to be clarified with the user before this action can safely run?",
        {"true": "a required detail is missing or ambiguous (which instance? which environment?); ask before acting",
         "false": "everything needed to act is present and unambiguous"}),
}

# Below this confidence on the grounding/appropriateness judgements, the gate does not trust the
# model to act alone (fail-closed): it clarifies, or asks a human when confirm_when_unsure is set.
# Tuned against the deployed hobson-v19 decider: grounded calls return ~0.55-0.60 confidence on
# this phrasing, so a 0.60 floor sent every call to CLARIFY. 0.55 lets clearly-grounded read-only
# calls PROCEED while still catching the genuinely uncertain ones. See policy.py and evaluation/.
CONFIDENCE_FLOOR = 0.55


class AWSOperationGuard(InterventionHandler):
    """Strands intervention that gates every AWS tool call through Decider 2B + a fail-closed policy."""

    name = "aws-operation-guard"

    def __init__(self, decider: Decider, yes: float = 0.5, confidence_floor: float = CONFIDENCE_FLOOR,
                 confirm_when_unsure: bool = False):
        self.decider = decider
        self.yes = yes
        self.confidence_floor = confidence_floor
        self.confirm_when_unsure = confirm_when_unsure
        self.log: list[dict[str, Any]] = []
        self._guided: set[str] = set()  # calls already sent back this turn; an unchanged retry is denied

    def before_invocation(self, event, **kwargs):
        self._guided.clear()  # a new user message: previously guided calls may now be justified
        return Proceed()

    def before_tool_call(self, event, **kwargs):
        name = event.tool_use["name"]
        args = event.tool_use.get("input") or {}
        # Fail-closed: every tool call is gated. A tool that is neither an allowed CloudGuard tool
        # nor a known destructive one is still unknown, and the policy denies it outright (below)
        # rather than letting it run. Nothing short-circuits to Proceed before the policy.
        sig = f"{name}:{json.dumps(args, sort_keys=True)}"

        if sig in self._guided:  # Guide must converge: the same guided call again, unchanged, is denied
            rec = self._record(name, args, None, "DENY", "retried a call that was already sent back for clarification", 0.0)
            return Deny(reason="This exact action was already held for clarification. Ask the user for the missing detail instead of retrying.")

        # Facts code owns, computed before and independently of the model (fail-closed inputs).
        validation = validate_arguments(name, args)
        pin = PolicyInput(
            tool=name,
            args=args,
            allowed=name in ALLOWED_TOOLS,
            destructive=name in DESTRUCTIVE_TOOLS,
            args_valid=validation.ok,
            validation_error=validation.error,
        )

        # Hard, code-owned DENY (destructive or unknown tool) does not need the model: deny in code.
        # This keeps the gate safe even if the decider is unavailable, and avoids a wasted call.
        if pin.destructive or not pin.allowed:
            outcome = decide(pin, {"args_grounded": 0.0, "appropriate": 0.0, "needs_clarify": 1.0}, 0.0,
                             yes=self.yes, confidence_floor=self.confidence_floor)
            self._record(name, args, None, outcome.action, outcome.reason, 0.0, decider_ms=0, decider_ok=True,
                         args_valid=validation.ok)
            return Deny(reason=outcome.reason)

        # Ask Strands Decider 2B the three language-level judgements in one forward pass.
        state = (
            "A conversation between a user and CloudGuard AI, an AWS operations assistant, then a "
            "tool call the assistant proposes to make.\n\n"
            f"--- CONVERSATION ---\n{render_messages(event.agent.messages)}\n\n"
            f"--- PROPOSED TOOL CALL ---\ntool: {name}\narguments: {json.dumps(args)}"
        )
        try:
            a = self.decider.ask(state, QUESTIONS)
            probs = {
                "args_grounded": float(a["args_grounded"].p_yes or 0.0),
                "appropriate": float(a["appropriate"].p_yes or 0.0),
                "needs_clarify": float(a["needs_clarify"].p_yes or 0.0),
            }
            confidence = min(a["args_grounded"].confidence, a["appropriate"].confidence)
            decider_ms = round(self.decider.last_latency_ms or 0)
            decider_ok = True
        except DeciderError as exc:
            # Fail closed: no usable decision means we never run the action automatically.
            probs = {"args_grounded": 0.0, "appropriate": 0.0, "needs_clarify": 1.0}
            confidence = 0.0
            decider_ms = round(self.decider.last_latency_ms or 0)
            decider_ok = False
            pin.validation_error = pin.validation_error or f"decider unavailable: {exc}"

        outcome = decide(pin, probs, confidence, yes=self.yes, confidence_floor=self.confidence_floor)

        rec = self._record(name, args, probs, outcome.action, outcome.reason, confidence,
                           decider_ms=decider_ms, decider_ok=decider_ok, args_valid=validation.ok)

        if outcome.action == "DENY":
            return Deny(reason=outcome.reason)
        if outcome.action == "CLARIFY":
            if self.confirm_when_unsure and outcome.confirmable:
                rec["verdict"] = "confirm"
                return Confirm(prompt=f"Approve {name} with {json.dumps(args)}? ({outcome.reason})", response="yes")
            self._guided.add(sig)
            return Guide(feedback=outcome.reason)
        return Proceed()

    def _record(self, name, args, probs, action, reason, confidence, *, decider_ms=0,
                decider_ok=True, args_valid=True) -> dict[str, Any]:
        rec: dict[str, Any] = {
            "pattern": PATTERN_TAG,
            "tool": name,
            "args": args,
            "verdict": action.lower(),
            "reason": reason,
            "confidence": round(confidence, 3),
            "args_valid": args_valid,
            "decider_ok": decider_ok,
            "decider_ms": decider_ms,
        }
        if probs:
            for k, v in probs.items():
                rec[k] = round(v, 3)
        self.log.append(rec)
        return rec
