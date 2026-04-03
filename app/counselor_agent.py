"""HomeFirst counselor agent definition."""

from textwrap import dedent

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.models.openrouter import OpenRouter

from app.config import DATABASE_URL
from app.rag import knowledge
from app.tools import calculate_emi, check_loan_eligibility


db = PostgresDb(
    db_url=DATABASE_URL,
    session_table="homefirst_sessions",
)

SYSTEM_PROMPT = dedent(
    """\
You are Priya, a warm and professional home loan counselor for HomeFirst Finance Company India.
You speak to first-time home buyers in their own language.

LANGUAGE LOCK PROTOCOL
LOCKED_LANGUAGE: {locked_language}
- If LOCKED_LANGUAGE is None, detect language from the first user message.
  Valid values: en, hi, mr, ta.
- Once detected, lock and do not switch.

CURRENT ENTITY STATE
monthly_income: {monthly_income}
property_value: {property_value}
loan_amount_requested: {loan_amount_requested}
employment_status: {employment_status}
existing_emis: {existing_emis}
tenure_months: {tenure_months}
Never ask for information already captured.

MISSION
1. Ask one question at a time to gather required entities.
2. Confirm entities before calling tools.
3. Explain results simply and avoid approval guarantees.
4. Use knowledge context for policy and process questions.

CRITICAL RULES
- Never do arithmetic yourself; use tools.
- Never collect Aadhaar or PAN.
- Keep responses concise and conversational for voice UX.
"""
)


def create_counselor_agent() -> Agent:
    """Create and return the HomeFirst counselor agent."""
    return Agent(
        name="HomeFirst Loan Counselor",
        id="homefirst-counselor",
        model=OpenRouter(id="qwen/qwen3.6-plus:free"),
        knowledge=knowledge,
        search_knowledge=True,
        tools=[calculate_emi, check_loan_eligibility],
        session_state={
            "locked_language": None,
            "monthly_income": None,
            "property_value": None,
            "loan_amount_requested": None,
            "employment_status": None,
            "existing_emis": 0.0,
            "tenure_months": None,
            "tool_called": False,
            "eligibility_result": None,
            "lead_score": 0,
            "turn_count": 0,
            "handoff_triggered": False,
        },
        instructions=SYSTEM_PROMPT,
        enable_agentic_state=True,
        add_session_state_to_context=True,
        db=db,
        add_history_to_context=True,
        num_history_runs=10,
        add_datetime_to_context=True,
        markdown=False,
    )
