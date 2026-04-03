"""Pydantic models for entity state and tool outputs."""
from typing import List, Optional

from pydantic import BaseModel, Field


class EntityState(BaseModel):
    locked_language: Optional[str] = Field(None, description="Locked language code: en, hi, mr, ta")
    monthly_income: Optional[float] = None
    property_value: Optional[float] = None
    loan_amount_requested: Optional[float] = None
    employment_status: Optional[str] = None
    existing_emis: Optional[float] = Field(default=0.0)
    tenure_months: Optional[int] = None
    tool_called: bool = False
    eligibility_result: Optional[dict] = None
    lead_score: int = 0
    turn_count: int = 0
    rag_chunks_used: List[str] = Field(default_factory=list)
    handoff_triggered: bool = False


class EMIResult(BaseModel):
    emi: float
    total_payable: float
    total_interest: float


class EligibilityResult(BaseModel):
    status: str
    eligible_amount: float
    reason: str
    recommended_emi: float
    foir_used: float
    ltv_cap: float
