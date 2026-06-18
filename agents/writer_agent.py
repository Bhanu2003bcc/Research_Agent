"""
agents/writer_agent.py
Node 7 – Writer Agent
"""
from __future__ import annotations
from typing import Optional

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from core.config import get_settings
from core.logging import get_logger
from core.models import CriticFeedback, DocumentChunk, PipelineState

logger = get_logger(__name__)

_WRITER_SYSTEM = """\
You are a meticulous research analyst tasked with writing a comprehensive,
fact-grounded answer to a research question.

STRICT GROUNDING INSTRUCTIONS:
1. Base your answer EXCLUSIVELY on the provided SOURCE CHUNKS.
2. Every single factual claim MUST be directly and explicitly supported by a provided source.
3. For every claim you make, you MUST append an inline citation referring to the source URL, formatted exactly as: [Source: <url>]. Do not group multiple urls or synthesize urls.
4. Do NOT fabricate, assume, extrapolate, or introduce any external information that is not explicitly present in the provided source chunks. If the sources do not mention a fact, it is considered non-existent for this task.
5. If the provided source chunks do not contain sufficient information to answer the question, state that clearly and present only what can be verified.
6. Only cite URLs that are explicitly listed in the SOURCE CHUNKS context. Do not invent URLs or use links not present in the context.
7. Write in clear, professional prose. Structure with headings, lists, and bold text for clarity.
"""

_REFINEMENT_ADDENDUM = """\

You are now REVISING a previous draft. The critic found the following issues:

Factual correctness score: {factual_score:.2f}
Completeness score: {completeness_score:.2f}
Hallucination risk: {hallucination_risk:.2f}

Missing information the revision must address:
{missing}

Concrete improvement suggestions:
{suggestions}

Produce an improved answer that addresses ALL of the above.
Keep all valid inline citations; add new ones where appropriate.
"""


def _build_context(chunks: list[DocumentChunk]) -> str:
    parts: list[str] = []
    seen_urls: set[str] = set()

    for chunk in chunks:
        url_tag = f"[Source: {chunk.source_url}]"
        if chunk.source_url not in seen_urls:
            seen_urls.add(chunk.source_url)
            header = f"### {chunk.source_title}\n{url_tag}"
        else:
            header = url_tag
        parts.append(f"{header}\n{chunk.text}\n")

    return "\n---\n".join(parts)


def _build_prompt(
    query: str,
    context: str,
    previous_draft: Optional[str],
    critic_feedback: Optional[CriticFeedback],
) -> str:
    if previous_draft and critic_feedback:
        missing = "\n".join(
            f"  - {m}" for m in (critic_feedback.missing_information or ["None"])
        )
        suggestions = "\n".join(
            f"  - {s}"
            for s in (critic_feedback.improvement_suggestions or ["None"])
        )
        refinement_note = _REFINEMENT_ADDENDUM.format(
            factual_score=critic_feedback.factual_correctness_score,
            completeness_score=critic_feedback.completeness_score,
            hallucination_risk=critic_feedback.hallucination_risk,
            missing=missing,
            suggestions=suggestions,
        )
        return (
            f"{refinement_note}\n\n"
            f"PREVIOUS DRAFT:\n{previous_draft}\n\n"
            f"SOURCE CHUNKS:\n{context}\n\n"
            f"RESEARCH QUESTION:\n{query}\n\n"
            "REVISED ANSWER:"
        )

    return (
        f"SOURCE CHUNKS:\n{context}\n\n"
        f"RESEARCH QUESTION:\n{query}\n\n"
        "ANSWER:"
    )


async def writer_agent_node(state: PipelineState) -> dict:
    """
    LangGraph node.
    Reads:  state['query'], state['retrieved_chunks'],
            state['draft_answer'] (if refinement), state['critic_feedback']
    Writes: state['draft_answer']
    """
    settings = get_settings()

    retrieved_chunks = state.get("retrieved_chunks", [])
    if not retrieved_chunks:
        logger.warning("writer_agent_no_chunks")
        return {
            "draft_answer": (
                "Insufficient source material was retrieved to answer this query."
            )
        }

    context = _build_context(retrieved_chunks)
    draft_answer = state.get("draft_answer", "")
    critic_feedback = state.get("critic_feedback")
    is_refinement = bool(draft_answer and critic_feedback)

    prompt = _build_prompt(
        query=state.get("query", ""),
        context=context,
        previous_draft=draft_answer if is_refinement else None,
        critic_feedback=critic_feedback if is_refinement else None,
    )

    logger.info(
        "writer_agent_start",
        is_refinement=is_refinement,
        iteration=state.get("refinement_iteration", 0),
    )

    llm = ChatGroq(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        groq_api_key=settings.groq_api_key,
    )

    messages = [
        SystemMessage(content=_WRITER_SYSTEM),
        HumanMessage(content=prompt),
    ]

    response = await llm.ainvoke(messages)
    draft = response.content.strip()

    logger.info("writer_agent_done", draft_length=len(draft))
    return {"draft_answer": draft}
