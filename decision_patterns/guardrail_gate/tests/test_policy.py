"""Unit tests for the standalone guardrail_gate policy. No decider, no network, no AWS."""

from __future__ import annotations

import sys
from pathlib import Path

# Make the repo root importable so `decision_patterns.guardrail_gate` resolves when run directly.
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from decision_patterns.guardrail_gate import PolicyInput, decide  # noqa: E402

GROUNDED = {"args_grounded": 0.95, "appropriate": 0.95, "needs_clarify": 0.05}


def _pin(tool="get_ec2_metrics", allowed=True, destructive=False, valid=True, err=None):
    return PolicyInput(tool=tool, args={}, allowed=allowed, destructive=destructive, args_valid=valid, validation_error=err)


def test_grounded_allowed_call_proceeds():
    assert decide(_pin(), GROUNDED, 0.9).action == "PROCEED"


def test_destructive_tool_is_denied_even_when_model_approves():
    # The model "likes" the call, but a destructive tool must be denied regardless (fail-closed).
    out = decide(_pin(tool="terminate_ec2_instance", destructive=True), GROUNDED, 0.99)
    assert out.action == "DENY"


def test_unknown_tool_is_denied():
    assert decide(_pin(tool="rm_minus_rf", allowed=False), GROUNDED, 0.9).action == "DENY"


def test_ungrounded_arguments_clarify():
    # Legitimate, appropriate request with a fabricated value -> CLARIFY (ask), not DENY.
    probs = {"args_grounded": 0.1, "appropriate": 0.9, "needs_clarify": 0.2}
    assert decide(_pin(), probs, 0.9).action == "CLARIFY"


def test_inappropriate_action_is_denied():
    probs = {"args_grounded": 0.9, "appropriate": 0.1, "needs_clarify": 0.2}
    assert decide(_pin(), probs, 0.9).action == "DENY"


def test_missing_information_clarifies():
    probs = {"args_grounded": 0.9, "appropriate": 0.9, "needs_clarify": 0.9}
    assert decide(_pin(), probs, 0.9).action == "CLARIFY"


def test_low_confidence_clarifies_and_is_confirmable():
    out = decide(_pin(), GROUNDED, 0.4, confidence_floor=0.6)
    assert out.action == "CLARIFY" and out.confirmable


def test_invalid_arguments_clarify():
    out = decide(_pin(valid=False, err="bad instance id"), GROUNDED, 0.9)
    assert out.action == "CLARIFY" and "bad instance id" in out.reason


def test_fail_closed_on_decider_outage():
    # The handler feeds zeros + a validation note when the decider errored; grounding<0.5 -> DENY.
    probs = {"args_grounded": 0.0, "appropriate": 0.0, "needs_clarify": 1.0}
    assert decide(_pin(err="decider unavailable: boom"), probs, 0.0).action == "DENY"
