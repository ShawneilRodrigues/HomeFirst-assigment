"""Deterministic lead scoring logic."""

from app.config import LEAD_SCORE_HANDOFF_THRESHOLD


def compute_lead_score(entity_state: dict, user_message: str = "") -> int:
    """Compute a lead score from 0-10."""
    score = 0

    core_entities = ["monthly_income", "property_value", "loan_amount_requested", "employment_status"]
    if all(entity_state.get(e) for e in core_entities):
        score += 3

    elig = entity_state.get("eligibility_result")
    if elig and isinstance(elig, dict) and elig.get("status") == "APPROVED":
        score += 3

    high_intent_phrases = [
        "when can i apply",
        "how to proceed",
        "kab milega loan",
        "next step",
        "aage kya karna hai",
        "apply karna hai",
        "documents bhejun",
        "ready to apply",
    ]
    msg_lower = user_message.lower()
    if any(phrase in msg_lower for phrase in high_intent_phrases):
        score += 2

    doc_phrases = ["documents", "dastavez", "kya chahiye", "papers", "kagaz"]
    if any(phrase in msg_lower for phrase in doc_phrases):
        score += 1

    if entity_state.get("tenure_months"):
        score += 1

    return min(score, 10)


def should_handoff(score: int) -> bool:
    return score >= LEAD_SCORE_HANDOFF_THRESHOLD
