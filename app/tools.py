"""Deterministic tool functions; the LLM does not do arithmetic."""
import json

from agno.run import RunContext

from app.config import DEFAULT_INTEREST_RATE, FOIR_LIMIT


def calculate_emi(
    run_context: RunContext,
    principal: float,
    annual_rate: float,
    tenure_months: int,
) -> str:
    """Calculate EMI and return a JSON payload."""
    if principal <= 0 or annual_rate <= 0 or tenure_months <= 0:
        return json.dumps({"error": "All inputs must be positive numbers."})

    r = annual_rate / 12 / 100
    n = tenure_months
    emi = principal * r * ((1 + r) ** n) / (((1 + r) ** n) - 1)
    total_payable = emi * n
    total_interest = total_payable - principal

    result = {
        "emi": round(emi, 2),
        "total_payable": round(total_payable, 2),
        "total_interest": round(total_interest, 2),
    }

    run_context.session_state["tool_called"] = True
    run_context.session_state["eligibility_result"] = result
    return json.dumps(result)


def check_loan_eligibility(
    run_context: RunContext,
    monthly_income: float,
    property_value: float,
    loan_requested: float,
    existing_emis: float,
    employment_status: str,
    tenure_months: int,
    annual_rate: float = DEFAULT_INTEREST_RATE,
) -> str:
    """Check home loan eligibility based on FOIR and LTV norms."""
    _ = employment_status
    available_emi = monthly_income * FOIR_LIMIT - existing_emis
    if available_emi <= 0:
        result = {
            "status": "REJECTED",
            "eligible_amount": 0,
            "reason": "FOIR exceeded - existing EMIs consume more than 50% of income.",
            "recommended_emi": 0,
            "foir_used": round((existing_emis / monthly_income) * 100, 2) if monthly_income > 0 else 0,
            "ltv_cap": 0,
        }
        run_context.session_state["tool_called"] = True
        run_context.session_state["eligibility_result"] = result
        return json.dumps(result)

    if property_value < 3000000:
        max_ltv = 0.90
    elif property_value <= 7500000:
        max_ltv = 0.80
    else:
        max_ltv = 0.75

    max_loan_ltv = property_value * max_ltv

    r = annual_rate / 12 / 100
    n = tenure_months
    if r > 0 and n > 0:
        max_loan_foir = available_emi * (((1 + r) ** n) - 1) / (r * ((1 + r) ** n))
    else:
        max_loan_foir = 0

    eligible_amount = min(max_loan_ltv, max_loan_foir, loan_requested)

    if eligible_amount >= loan_requested:
        status = "APPROVED"
        reason = "Full loan amount is within FOIR and LTV limits."
    elif eligible_amount > 0:
        status = "PARTIAL"
        reason = f"Eligible for Rs {eligible_amount:,.0f} instead of requested Rs {loan_requested:,.0f}."
    else:
        status = "REJECTED"
        reason = "Loan amount exceeds both FOIR and LTV limits."

    if eligible_amount > 0:
        rec_emi = eligible_amount * r * ((1 + r) ** n) / (((1 + r) ** n) - 1)
    else:
        rec_emi = 0

    result = {
        "status": status,
        "eligible_amount": round(eligible_amount, 2),
        "reason": reason,
        "recommended_emi": round(rec_emi, 2),
        "foir_used": round(((existing_emis + rec_emi) / monthly_income) * 100, 2) if monthly_income > 0 else 0,
        "ltv_cap": max_ltv * 100,
    }

    run_context.session_state["tool_called"] = True
    run_context.session_state["eligibility_result"] = result
    return json.dumps(result)
