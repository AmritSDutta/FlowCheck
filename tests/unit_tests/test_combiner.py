from __future__ import annotations
import pytest

from src.flow_agent.data_objs.business_objs import DecisionOutput, CombinedPlan


# --- Example evaluators used in tests ---
@pytest.fixture
def example_evals():
    return [
        DecisionOutput(
            decision_id="reset_vpn_profile",
            decision=True,
            confidence=0.87,
            model="gpt-5-mini-v1",
            notes="Detected repeated VPN disconnects",
            latency_ms=320,
        ),
        DecisionOutput(
            decision_id="restart_sso_session",
            decision=True,
            confidence=0.58,
            model="gpt-5-mini-v1",
            notes="SSO token refresh errors ambiguous",
            latency_ms=280,
        ),
    ]


def test_default_threshold_disables_low_confidence(example_evals):
    plan = CombinedPlan.assemble_from_evaluators(
        example_evals, conf_threshold=0.6, summary_notes="Reset VPN recommended; SSO ambiguous."
    )
    assert plan.reset_vpn_profile is True
    assert plan.restart_sso_session is False  # 0.58 < 0.6
    assert plan.confidence == 0.87
    assert plan.notes == "Reset VPN recommended; SSO ambiguous."


def test_lower_global_threshold_enables_sso(example_evals):
    plan = CombinedPlan.assemble_from_evaluators(
        example_evals, conf_threshold=0.5, summary_notes="Lower threshold test"
    )
    assert plan.reset_vpn_profile is True
    assert plan.restart_sso_session is True  # 0.58 >= 0.5
    assert plan.confidence == 0.87


def test_per_decision_threshold_enables_sso_only(example_evals):
    plan = CombinedPlan.assemble_from_evaluators(
        example_evals,
        conf_threshold=0.5,
        summary_notes="Per-decision threshold test"
    )
    assert plan.reset_vpn_profile is True
    assert plan.restart_sso_session is True  # per-decision threshold 0.55 allows 0.58
    assert plan.confidence == 0.87


def test_no_decisions_above_threshold_returns_confidence_zero():
    low_conf_evals = [
        DecisionOutput(
            decision_id="reset_vpn_profile",
            decision=True,
            confidence=0.2,
            model="gpt-5-mini-v1",
            notes="low confidence",
            latency_ms=100,
        )
    ]
    plan = CombinedPlan.assemble_from_evaluators(low_conf_evals, conf_threshold=0.5)
    assert plan.reset_vpn_profile is False
    assert plan.confidence == 0.0


"""
subject: repeated VPN disconnects and SSO failures.

Hi team,

Please take a look at this — ticket INC-448291 has been getting worse.  
User is really frustrated at this point. They’re on priority P3, but the impact is growing.

Full description:  
Over the last 24 hours, their VPN drops almost every hour. On top of that, the SSO token refresh keeps failing, 
which means they can’t log into Jira or Confluence at all. They’re basically blocked from doing any internal work. 
They’ve attached logs from today hoping it helps (log_2025_11_20.zip).

Requested action from the user: *“Please stabilize my access — I can’t keep getting kicked out like this.”*
Feels like this might need a VPN profile reset + SSO session restart, but I’ll leave it to the automation to decide.
Thanks.
"""
