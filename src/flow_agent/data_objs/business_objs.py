from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

DecisionID = Literal[
    "generate_summary",
    "reset_vpn_profile",
    "restart_sso_session",
    "run_connectivity_diagnostics",
    "update_internal_record",
    "send_notification",
    "approval_required",
]


class DecisionOutput(BaseModel):
    decision_id: DecisionID
    decision: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    model: str
    notes: Optional[str] = None
    latency_ms: Optional[int] = Field(None, ge=0)

    # Normalize/round confidence at validation time
    @field_validator("confidence", mode="before")
    @classmethod
    def _round_confidence(cls, v):
        try:
            return round(float(v), 3)
        except Exception:
            raise ValueError("confidence must be a numeric value between 0.0 and 1.0")


class CombinedPlan(BaseModel):
    # Decision flags
    generate_summary: bool = False
    reset_vpn_profile: bool = False
    restart_sso_session: bool = False
    run_connectivity_diagnostics: bool = False
    update_internal_record: bool = False
    send_notification: bool = False
    approval_required: bool = False

    # Aggregated metadata
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    notes: Optional[str] = None

    @classmethod
    def assemble_from_evaluators(
            cls,
            evals: List[DecisionOutput],
            conf_threshold: float = 0.6,
            summary_notes: Optional[str] = None,
    ) -> "CombinedPlan":
        """
        Deterministic combiner:
        - Enable a decision if any evaluator for that decision_id returned decision==True
          with confidence >= conf_threshold.
        - approval_required follows same rule.
        - confidence = max(confidence of enabled decisions) or 0.0.
        - notes = summary_notes (combiner LLM or deterministic concat).
        """
        keys = {
            "generate_summary",
            "reset_vpn_profile",
            "restart_sso_session",
            "run_connectivity_diagnostics",
            "update_internal_record",
            "send_notification",
            "approval_required",
        }

        mapping = {k: False for k in keys}
        true_confidences: List[float] = []

        for d in evals:
            if d.decision and d.confidence >= conf_threshold:
                mapping[d.decision_id] = True
                true_confidences.append(d.confidence)

        overall_conf = round(max(true_confidences) if true_confidences else 0.0, 3)

        return cls(
            generate_summary=mapping["generate_summary"],
            reset_vpn_profile=mapping["reset_vpn_profile"],
            restart_sso_session=mapping["restart_sso_session"],
            run_connectivity_diagnostics=mapping["run_connectivity_diagnostics"],
            update_internal_record=mapping["update_internal_record"],
            send_notification=mapping["send_notification"],
            approval_required=mapping["approval_required"],
            confidence=overall_conf,
            notes=summary_notes,
        )


# ---- Minimal example usage ----
if __name__ == "__main__":
    examples = [
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

    plan = CombinedPlan.assemble_from_evaluators(examples, conf_threshold=0.6,
                                                 summary_notes="Reset VPN recommended; SSO ambiguous.")
    print(plan.model_dump_json(indent=2))
