"""
agents/critic_agent.py
Node 8 – Critic Agent
"""
from __future__ import annotations
import json
import re

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from core.config import get_settings
from core.logging import get_logger
from core.models import CriticFeedback, PipelineState

logger = get_logger(__name__)

_CRITIC_SYSTEM = """\
You are a rigorous academic fact-checker and research editor.
Your job is to critically evaluate a draft research answer against
the provided source material and return a JSON evaluation.

OUTPUT FORMAT – return ONLY valid JSON, no prose before or after:
{
  "factual_correctness_score": <float 0-1>,
  "completeness_score": <float 0-1>,
  "hallucination_risk": <float 0-1>,
  "missing_information": ["<item>", ...],
  "improvement_suggestions": ["<suggestion>", ...],
  "overall_quality": <float 0-1>
}

EVALUATION CRITERIA & HALLUCINATION POLICY:
- factual_correctness_score: Check every claim in the draft answer. Are all claims directly supported by the provided sources? If not, penalize this score heavily.
- completeness_score: Does the answer fully address all aspects of the query?
- hallucination_risk: Identify any statement, metric, claim, or detail that is NOT explicitly mentioned in the source material. Even if a claim is likely true, if it is NOT in the source material, classify it as a hallucination (hallucination_risk > 0.0) and describe the unverified claim in the suggestions.
- missing_information: List key facts from the source material that are relevant to the query but missing from the draft.
- improvement_suggestions: List concrete edits to align the draft with the source material and remove any hallucinations.
- overall_quality: Weighted aggregate of the above scores. For high-quality, factual answers, this should reflect high correctness and low hallucination risk.
"""


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM output even if surrounded by markdown fences."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError(f"No JSON found in critic output:\n{text[:500]}")


async def critic_agent_node(state: PipelineState) -> dict:
    """
    LangGraph node.
    Reads:  state['draft_answer'], state['query'], state['retrieved_chunks']
    Writes: state['critic_feedback']
    """
    settings = get_settings()

    draft_answer = state.get("draft_answer", "")
    if not draft_answer:
        logger.warning("critic_agent_no_draft")
        return {"critic_feedback": None}

    retrieved_chunks = state.get("retrieved_chunks", [])
    
    # Build complete source text context so critic can fact-check the whole text
    parts: list[str] = []
    seen_urls: set[str] = set()
    for chunk in retrieved_chunks:
        url_tag = f"[Source: {chunk.source_url}]"
        if chunk.source_url not in seen_urls:
            seen_urls.add(chunk.source_url)
            header = f"### {chunk.source_title}\n{url_tag}"
        else:
            header = url_tag
        parts.append(f"{header}\n{chunk.text}\n")
    source_summary = "\n---\n".join(parts)

    prompt = (
        f"RESEARCH QUERY:\n{state.get('query', '')}\n\n"
        f"SOURCE MATERIAL:\n{source_summary}\n\n"
        f"DRAFT ANSWER TO EVALUATE:\n{draft_answer}\n\n"
        "Return your evaluation JSON now."
    )

    logger.info("critic_agent_start")

    llm = ChatGroq(
        model=settings.llm_model,
        temperature=0.0,
        max_tokens=1024,
        groq_api_key=settings.groq_api_key,
    )

    messages = [
        SystemMessage(content=_CRITIC_SYSTEM),
        HumanMessage(content=prompt),
    ]

    response = await llm.ainvoke(messages)

    try:
        raw = _extract_json(response.content)
        feedback = CriticFeedback(**raw)
        logger.info(
            "critic_agent_done",
            overall_quality=feedback.overall_quality,
            hallucination_risk=feedback.hallucination_risk,
        )
        return {"critic_feedback": feedback}
    except Exception as exc:
        logger.error("critic_parse_failed", error=str(exc))
        fallback = CriticFeedback(
            factual_correctness_score=0.7,
            completeness_score=0.7,
            hallucination_risk=0.3,
            missing_information=[],
            improvement_suggestions=["Could not parse critic output automatically."],
            overall_quality=0.7,
        )
        return {"critic_feedback": fallback}
