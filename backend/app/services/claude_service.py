"""Claude AI service for job scoring and application message drafting."""
import hashlib
import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.score import AIAuditLog, JobScore

# Module-level daily spend tracker: {date_str: total_usd}
_daily_spend: dict[str, float] = {}

# Pricing per million tokens (claude-sonnet-4-6)
_INPUT_COST_PER_M = 3.0
_OUTPUT_COST_PER_M = 15.0


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * _INPUT_COST_PER_M / 1_000_000) + (
        output_tokens * _OUTPUT_COST_PER_M / 1_000_000
    )


def _check_budget(estimated_additional: float) -> None:
    """Raise 402 if adding estimated_additional would exceed daily budget."""
    today = date.today().isoformat()
    current = _daily_spend.get(today, 0.0)
    if current + estimated_additional > settings.CLAUDE_DAILY_BUDGET_USD:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Daily AI budget exceeded. Spent ${current:.4f} of "
                f"${settings.CLAUDE_DAILY_BUDGET_USD:.2f} limit."
            ),
        )


def _record_spend(input_tokens: int, output_tokens: int) -> None:
    today = date.today().isoformat()
    cost = _estimate_cost(input_tokens, output_tokens)
    _daily_spend[today] = _daily_spend.get(today, 0.0) + cost


async def _log_ai_call(
    session: AsyncSession,
    event_type: str,
    entity_type: str,
    entity_id: uuid.UUID,
    model: str,
    prompt: str,
    input_tokens: int,
    output_tokens: int,
    result_summary: str,
) -> None:
    """Log an AI call to the audit log. Uses flush, not commit."""
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    log_entry = AIAuditLog(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        model=model,
        prompt_hash=prompt_hash,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        result_summary=result_summary,
    )
    session.add(log_entry)
    await session.flush()


def _require_api_key() -> str:
    """Return the API key or raise 503 if it's the placeholder."""
    key = settings.ANTHROPIC_API_KEY
    if not key or key.startswith("sk-ant-...") or key == "sk-ant-...":
        raise HTTPException(
            status_code=503,
            detail="Anthropic API key not configured. Set ANTHROPIC_API_KEY environment variable.",
        )
    return key


async def score_job_against_cv(
    job: Job,
    candidate: Candidate,
    session: AsyncSession,
) -> JobScore:
    """
    Score a job against a candidate's CV using Claude tool_use for structured output.
    Logs to ai_audit_log. Raises if daily budget exceeded.
    Returns a persisted JobScore.
    """
    import anthropic

    api_key = _require_api_key()

    # Check budget before calling (estimate 1000 input + 500 output tokens)
    _check_budget(_estimate_cost(1000, 500))

    cv_text = candidate.cv_raw_text or "No CV uploaded"

    prompt = f"""You are evaluating job fit. Score how well this job matches this candidate.

JOB TITLE: {job.title}
COMPANY: {job.company_name}
LOCATION: {job.city or "Not specified"}
SALARY: {job.salary_range or "Not specified"}
DESCRIPTION: {(job.description or "Not provided")[:2000]}
REQUIREMENTS: {(job.requirements or "Not provided")[:1000]}

CANDIDATE PROFILE:
{cv_text[:3000] if cv_text != "No CV uploaded" else "No CV uploaded"}

Use the score_job_match tool to return a structured evaluation."""

    tool_schema: dict[str, Any] = {
        "name": "score_job_match",
        "description": "Return a structured job-candidate match evaluation",
        "input_schema": {
            "type": "object",
            "properties": {
                "score": {
                    "type": "number",
                    "description": "Overall match score 0-100",
                },
                "breakdown": {
                    "type": "object",
                    "properties": {
                        "skills": {
                            "type": "number",
                            "description": "Skills match 0-25",
                        },
                        "experience": {
                            "type": "number",
                            "description": "Experience match 0-25",
                        },
                        "salary": {
                            "type": "number",
                            "description": "Salary match 0-25",
                        },
                        "culture": {
                            "type": "number",
                            "description": "Culture/location match 0-25",
                        },
                    },
                    "required": ["skills", "experience", "salary", "culture"],
                },
                "summary": {"type": "string"},
                "strengths": {"type": "array", "items": {"type": "string"}},
                "concerns": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["score", "breakdown", "summary"],
        },
    }

    client = anthropic.AsyncAnthropic(api_key=api_key)

    response = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=settings.CLAUDE_MAX_TOKENS,
        tools=[tool_schema],
        tool_choice={"type": "tool", "name": "score_job_match"},
        messages=[{"role": "user", "content": prompt}],
    )

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    # Record spend
    _record_spend(input_tokens, output_tokens)

    # Extract tool use result
    tool_result: dict[str, Any] = {}
    for block in response.content:
        if block.type == "tool_use" and block.name == "score_job_match":
            tool_result = block.input
            break

    if not tool_result:
        raise HTTPException(
            status_code=500,
            detail="Claude did not return a structured score result.",
        )

    breakdown = tool_result.get("breakdown", {})
    score_obj = JobScore(
        job_id=job.id,
        candidate_id=candidate.id,
        score=float(tool_result.get("score", 0)),
        score_breakdown={
            "skills": float(breakdown.get("skills", 0)),
            "experience": float(breakdown.get("experience", 0)),
            "salary": float(breakdown.get("salary", 0)),
            "culture": float(breakdown.get("culture", 0)),
        },
        match_summary=tool_result.get("summary", ""),
        strengths=tool_result.get("strengths", []),
        concerns=tool_result.get("concerns", []),
        model_used=settings.CLAUDE_MODEL,
        prompt_tokens=input_tokens,
        completion_tokens=output_tokens,
    )
    session.add(score_obj)
    await session.flush()
    await session.refresh(score_obj)

    # Log the call
    await _log_ai_call(
        session=session,
        event_type="score",
        entity_type="job",
        entity_id=job.id,
        model=settings.CLAUDE_MODEL,
        prompt=prompt,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        result_summary=f"Score: {score_obj.score:.1f}/100 — {score_obj.match_summary[:200]}",
    )

    return score_obj


async def draft_application_message(
    job: Job,
    candidate: Candidate,
    score: JobScore,
    session: AsyncSession,
) -> str:
    """
    Generate a personalized application message using Claude.
    Logs to ai_audit_log.
    Returns the draft message string.
    """
    import anthropic

    api_key = _require_api_key()

    # Check budget (estimate 800 input + 300 output)
    _check_budget(_estimate_cost(800, 300))

    cv_text = candidate.cv_raw_text or "No CV"
    strengths_str = ", ".join(score.strengths) if score.strengths else "Not specified"

    prompt = f"""You are writing a professional job application message in Chinese (for BOSS Zhipin).
Keep it concise (3-4 sentences), genuine, and specific to the role.
Do NOT invent any facts not present in the candidate profile.
Do NOT be spammy or use generic templates.

JOB: {job.title} at {job.company_name}
CANDIDATE NAME: {candidate.name}
MATCH SCORE: {score.score:.0f}/100
KEY STRENGTHS: {strengths_str}
CV SUMMARY: {cv_text[:1500] if cv_text != "No CV" else "No CV"}

Write only the message, no preamble."""

    client = anthropic.AsyncAnthropic(api_key=api_key)

    response = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    _record_spend(input_tokens, output_tokens)

    draft = ""
    for block in response.content:
        if hasattr(block, "text"):
            draft = block.text.strip()
            break

    if not draft:
        draft = "您好，我对贵公司的职位非常感兴趣，希望有机会进一步交流。"

    # Log the call
    await _log_ai_call(
        session=session,
        event_type="draft_message",
        entity_type="job",
        entity_id=job.id,
        model=settings.CLAUDE_MODEL,
        prompt=prompt,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        result_summary=draft[:200],
    )

    return draft
