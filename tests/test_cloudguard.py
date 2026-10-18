"""CloudGuard AI: the agent's own decision gate, policy, validation and tools (offline)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fakes import FakeDecider

from strands.interventions import Confirm, Deny, Guide, Proceed

from agent.decision import AWSOperationGuard, PATTERN_TAG, QUESTIONS
from agent.policy import PolicyInput, decide, validate_arguments
from agent.tools import get_cloudwatch_alarms, get_ec2_instance_details, get_ec2_metrics


# --- the decision pattern is labelled correctly -------------------------------------------------

def test_pattern_tag_and_questions():
    assert PATTERN_TAG == "#guardrails"
    assert set(QUESTIONS) == {"args_grounded", "appropriate", "needs_clarify"}
    assert all(q["type"] == "noul" for q in QUESTIONS.values())


# --- structural validation (code, not the model) -----------------------------------------------

@pytest.mark.parametrize("iid,ok", [
    ("i-1234567890abcdef0", True), ("i-0abc1111", True), ("", False), ("not-an-id", False), ("i-xyz", False)])
def test_instance_id_validation(iid, ok):
    assert validate_arguments("get_ec2_instance_details", {"instance_id": iid}).ok is ok


def test_unknown_metric_is_rejected():
    assert not validate_arguments("get_ec2_metrics", {"instance_id": "i-1234567890abcdef0", "metric": "MemUsage"}).ok
    assert validate_arguments("get_ec2_metrics", {"instance_id": "i-1234567890abcdef0", "metric": "CPUUtilization"}).ok


# --- the fail-closed policy ---------------------------------------------------------------------

GROUNDED = {"args_grounded": 0.95, "appropriate": 0.95, "needs_clarify": 0.05}


def _pin(tool="get_ec2_metrics", allowed=True, destructive=False, valid=True, err=None):
    return PolicyInput(tool=tool, args={}, allowed=allowed, destructive=destructive, args_valid=valid, validation_error=err)


def test_policy_proceeds_on_grounded_read_only():
    assert decide(_pin(), GROUNDED, 0.9).action == "PROCEED"


def test_policy_denies_destructive_even_if_model_approves():
    assert decide(_pin("terminate_ec2_instance", destructive=True), GROUNDED, 0.99).action == "DENY"


def test_policy_denies_unknown_tool():
    assert decide(_pin("do_magic", allowed=False), GROUNDED, 0.9).action == "DENY"


def test_policy_clarifies_on_ungrounded_but_appropriate():
    # Ungrounded argument on a legitimate request: ask the user, do not hard-deny.
    assert decide(_pin(), {"args_grounded": 0.1, "appropriate": 0.9, "needs_clarify": 0.1}, 0.9).action == "CLARIFY"


def test_policy_denies_inappropriate_action():
    assert decide(_pin(), {"args_grounded": 0.9, "appropriate": 0.1, "needs_clarify": 0.1}, 0.9).action == "DENY"


def test_policy_clarifies_on_missing_info():
    assert decide(_pin(), {"args_grounded": 0.9, "appropriate": 0.9, "needs_clarify": 0.9}, 0.9).action == "CLARIFY"


def test_policy_clarifies_on_low_confidence():
    out = decide(_pin(), GROUNDED, 0.3, confidence_floor=0.6)
    assert out.action == "CLARIFY" and out.confirmable


def test_policy_clarifies_on_invalid_args():
    assert decide(_pin(valid=False, err="bad id"), GROUNDED, 0.9).action == "CLARIFY"


# --- the Strands intervention -------------------------------------------------------------------

def _event(tool, args, text="investigate high CPU on i-1234567890abcdef0"):
    return SimpleNamespace(tool_use={"name": tool, "input": args},
                           agent=SimpleNamespace(messages=[{"role": "user", "content": [{"text": text}]}]))


def _guard(rule, **kw):
    return AWSOperationGuard(FakeDecider(rule), **kw)


def test_guard_proceeds_on_grounded_read_only():
    g = _guard(lambda s, n, q: 0.95 if n != "needs_clarify" else 0.05)
    out = g.before_tool_call(_event("get_ec2_metrics", {"instance_id": "i-1234567890abcdef0", "metric": "CPUUtilization"}))
    assert isinstance(out, Proceed) and g.log[-1]["verdict"] == "proceed"


def test_guard_clarifies_on_fabricated_identifier():
    # Decider says ungrounded on a well-formed (17 hex) id: a legitimate request with a fabricated
    # value -> CLARIFY (ask which instance), not a hard DENY.
    g = _guard(lambda s, n, q: 0.05 if n == "args_grounded" else 0.9)
    out = g.before_tool_call(_event("get_ec2_metrics", {"instance_id": "i-00000000000000000", "metric": "CPUUtilization"}))
    assert isinstance(out, Guide)


def test_guard_denies_destructive_action():
    g = _guard(lambda s, n, q: 0.99)
    out = g.before_tool_call(_event("terminate_ec2_instance", {"instance_id": "i-1234567890abcdef0"}))
    assert isinstance(out, Deny)


def test_guard_clarifies_when_info_missing():
    g = _guard(lambda s, n, q: 0.95 if n in ("args_grounded", "appropriate", "needs_clarify") else 0.5)
    out = g.before_tool_call(_event("get_ec2_metrics", {"instance_id": "i-1234567890abcdef0", "metric": "CPUUtilization"}))
    assert isinstance(out, Guide)


def test_guard_converges_guide_to_deny():
    g = _guard(lambda s, n, q: 0.95 if n in ("args_grounded", "appropriate", "needs_clarify") else 0.5)
    ev = _event("get_ec2_metrics", {"instance_id": "i-1234567890abcdef0", "metric": "CPUUtilization"})
    assert isinstance(g.before_tool_call(ev), Guide)
    assert isinstance(g.before_tool_call(ev), Deny)


def test_guard_confirms_when_unsure_and_configured():
    g = _guard(lambda s, n, q: 0.5, confirm_when_unsure=True)  # confidence 0.5 < floor 0.6 -> confirmable
    out = g.before_tool_call(_event("get_ec2_metrics", {"instance_id": "i-1234567890abcdef0", "metric": "CPUUtilization"}))
    assert isinstance(out, Confirm)


def test_guard_records_audit_trace_fields():
    g = _guard(lambda s, n, q: 0.95 if n != "needs_clarify" else 0.05)
    g.before_tool_call(_event("get_ec2_metrics", {"instance_id": "i-1234567890abcdef0", "metric": "CPUUtilization"}))
    rec = g.log[-1]
    for key in ("pattern", "tool", "args", "verdict", "reason", "confidence", "args_valid", "decider_ok",
                "decider_ms", "args_grounded", "appropriate", "needs_clarify"):
        assert key in rec, key


def test_guard_fails_closed_when_decider_errors():
    from decider_kit import DeciderError

    class Boom:
        last_latency_ms = 0.0
        def ask(self, *a, **k):
            raise DeciderError("no decider")

    g = AWSOperationGuard(Boom())
    out = g.before_tool_call(_event("get_ec2_metrics", {"instance_id": "i-1234567890abcdef0", "metric": "CPUUtilization"}))
    assert isinstance(out, Deny) and g.log[-1]["decider_ok"] is False


# --- tools are simulated, read-only and clearly labelled ----------------------------------------

def test_tools_are_labelled_simulated():
    assert get_ec2_instance_details("i-1234567890abcdef0")["source"] == "simulated"
    assert get_ec2_metrics("i-1234567890abcdef0")["source"] == "simulated"
    assert get_cloudwatch_alarms()["source"] == "simulated"


def test_metrics_for_unknown_instance_errors_not_invents():
    out = get_ec2_metrics("i-ffffffffffffffff0")
    assert "error" in out and out["source"] == "simulated"
