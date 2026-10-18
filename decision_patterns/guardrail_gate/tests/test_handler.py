"""Tests for the Strands wiring: the gate returns the right intervention and converges."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from strands.interventions import Deny, Guide, Proceed  # noqa: E402

from decision_patterns.guardrail_gate import GuardrailGate  # noqa: E402
from fakes import FakeDecider  # noqa: E402

GUARDED = {"get_ec2_metrics"}
ALLOWED = {"get_ec2_metrics"}
DESTRUCTIVE = {"terminate_ec2_instance"}


def _event(tool, args):
    return SimpleNamespace(tool_use={"name": tool, "input": args},
                           agent=SimpleNamespace(messages=[{"role": "user", "content": [{"text": "investigate i-1234567890abcdef0"}]}]))


def _gate(rule):
    return GuardrailGate(FakeDecider(rule), guarded=GUARDED | DESTRUCTIVE, allowed=ALLOWED, destructive=DESTRUCTIVE)


def test_grounded_call_proceeds():
    g = _gate(lambda s, n, q: 0.95 if n != "needs_clarify" else 0.05)
    assert isinstance(g.before_tool_call(_event("get_ec2_metrics", {"instance_id": "i-1234567890abcdef0"})), Proceed)
    assert g.log[-1]["verdict"] == "proceed"


def test_ungrounded_call_clarifies():
    # Ungrounded but appropriate request -> CLARIFY (Guide), not DENY.
    g = _gate(lambda s, n, q: 0.1 if n == "args_grounded" else 0.9)
    assert isinstance(g.before_tool_call(_event("get_ec2_metrics", {"instance_id": "i-99999999999999999"})), Guide)


def test_destructive_call_is_denied_before_asking_the_model():
    g = _gate(lambda s, n, q: 0.99)
    assert isinstance(g.before_tool_call(_event("terminate_ec2_instance", {"instance_id": "i-1234567890abcdef0"})), Deny)


def test_unguarded_tool_proceeds_untouched():
    g = _gate(lambda s, n, q: 0.99)
    assert isinstance(g.before_tool_call(_event("some_other_tool", {})), Proceed)


def test_guide_converges_to_deny_on_retry():
    # needs_clarify high -> CLARIFY (Guide); the same call again, unchanged -> Deny.
    g = _gate(lambda s, n, q: 0.95 if n in ("args_grounded", "appropriate", "needs_clarify") else 0.5)
    ev = _event("get_ec2_metrics", {"instance_id": "i-1234567890abcdef0"})
    assert isinstance(g.before_tool_call(ev), Guide)
    assert isinstance(g.before_tool_call(ev), Deny)
