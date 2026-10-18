"""The Strands intervention that wires the gate into an agent's path.

`GuardrailGate` is a `strands.interventions.InterventionHandler`. The framework calls
`before_tool_call` before each tool runs; the gate asks Strands Decider 2B the three questions,
feeds the answers and the code-owned facts to the policy, and returns a Strands decision:
`Proceed`, `Guide` (CLARIFY - send the agent back to ask the user), `Deny`, or `Confirm`.

To reuse it, pass your own `allowed`, `destructive`, and `validate` callables; everything domain-
specific lives in those, so the gate itself stays generic.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from strands.interventions import Confirm, Deny, Guide, InterventionHandler, Proceed

from .policy import PolicyInput, decide
from .questions import CONFIDENCE_FLOOR, QUESTIONS


def _render(messages: list[dict[str, Any]], last: int = 12) -> str:
    lines = []
    for m in messages[-last:]:
        for block in m.get("content", []):
            if isinstance(block, dict) and "text" in block:
                lines.append(f"{m.get('role', '?')}: {block['text']}")
    return "\n".join(lines) or "(no conversation yet)"


class GuardrailGate(InterventionHandler):
    """Gate every guarded tool call through Decider 2B + a fail-closed policy."""

    name = "guardrail-gate"

    def __init__(
        self,
        decider: Any,
        guarded: set[str],
        allowed: set[str],
        destructive: set[str],
        validate: Callable[[str, dict[str, Any]], tuple[bool, str | None]] | None = None,
        yes: float = 0.5,
        confidence_floor: float = CONFIDENCE_FLOOR,
        confirm_when_unsure: bool = False,
    ):
        self.decider = decider
        self.guarded, self.allowed, self.destructive = guarded, allowed, destructive
        self.validate = validate or (lambda t, a: (True, None))
        self.yes, self.confidence_floor = yes, confidence_floor
        self.confirm_when_unsure = confirm_when_unsure
        self.log: list[dict[str, Any]] = []
        self._guided: set[str] = set()

    def before_invocation(self, event, **kwargs):
        self._guided.clear()
        return Proceed()

    def before_tool_call(self, event, **kwargs):
        name = event.tool_use["name"]
        if name not in self.guarded:
            return Proceed()
        args = event.tool_use.get("input") or {}
        sig = f"{name}:{json.dumps(args, sort_keys=True)}"
        if sig in self._guided:
            self.log.append({"tool": name, "args": args, "verdict": "deny", "reason": "retried a guided call"})
            return Deny(reason="This exact action was already held for clarification. Ask for the missing detail instead.")

        ok, err = self.validate(name, args)
        pin = PolicyInput(tool=name, args=args, allowed=name in self.allowed,
                          destructive=name in self.destructive, args_valid=ok, validation_error=err)

        try:
            a = self.decider.ask(self._state(event, name, args), QUESTIONS)
            probs = {k: float(a[k].p_yes or 0.0) for k in QUESTIONS}
            confidence = min(a["args_grounded"].confidence, a["appropriate"].confidence)
            decider_ok = True
        except Exception as exc:  # fail closed: no usable decision -> do not run
            probs = {"args_grounded": 0.0, "appropriate": 0.0, "needs_clarify": 1.0}
            confidence = 0.0
            decider_ok = False
            pin.validation_error = pin.validation_error or f"decider unavailable: {exc}"

        out = decide(pin, probs, confidence, yes=self.yes, confidence_floor=self.confidence_floor)
        rec = {"tool": name, "args": args, "verdict": out.action.lower(), "reason": out.reason,
               "confidence": round(confidence, 3), "decider_ok": decider_ok,
               "decider_ms": round(getattr(self.decider, "last_latency_ms", 0) or 0), **{k: round(v, 3) for k, v in probs.items()}}
        self.log.append(rec)

        if out.action == "DENY":
            return Deny(reason=out.reason)
        if out.action == "CLARIFY":
            if self.confirm_when_unsure and out.confirmable:
                return Confirm(prompt=f"Approve {name} with {json.dumps(args)}? ({out.reason})", response="yes")
            self._guided.add(sig)
            return Guide(feedback=out.reason)
        return Proceed()

    @staticmethod
    def _state(event, name: str, args: dict[str, Any]) -> str:
        return ("A conversation between a user and an AI assistant, then a tool call the assistant proposes.\n\n"
                f"--- CONVERSATION ---\n{_render(event.agent.messages)}\n\n"
                f"--- PROPOSED TOOL CALL ---\ntool: {name}\narguments: {json.dumps(args)}")
