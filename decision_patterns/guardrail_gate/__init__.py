"""guardrail_gate: a reusable Strands Decider 2B decision gate for tool calls.

Standalone, dependency-light mirror of CloudGuard AI's decision pattern (agent/decision.py +
agent/policy.py), packaged so another builder can read and lift it without the rest of the app.

    from decision_patterns.guardrail_gate import QUESTIONS, GuardrailGate, decide, PolicyInput

See README.md for the full write-up. The pattern:
  1. asks Strands Decider 2B three typed, language-level questions about a proposed tool call
     (grounded? appropriate? missing information?);
  2. combines the answers with code-owned facts (allowed? destructive? arguments valid?) in a
     deterministic, fail-closed policy;
  3. returns PROCEED / CLARIFY / DENY, wired as a Strands InterventionHandler before the tool runs.
"""

from .policy import PolicyInput, PolicyOutcome, decide
from .questions import CONFIDENCE_FLOOR, QUESTIONS

__all__ = [
    "QUESTIONS",
    "CONFIDENCE_FLOOR",
    "PolicyInput",
    "PolicyOutcome",
    "decide",
    "GuardrailGate",
]


def __getattr__(name: str):
    # Lazy import so `QUESTIONS`/`decide` work without strands installed.
    if name == "GuardrailGate":
        from .handler import GuardrailGate

        return GuardrailGate
    raise AttributeError(name)
