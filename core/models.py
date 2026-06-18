"""
core/models.py
All shared Pydantic data models for the multi-agent pipeline.
"""
from __future__ import annotations
from typing import Any, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field, HttpUrl
import time


# ---------------------------------------------------------------------------
# Search Layer
# ---------------------------------------------------------------------------

class SearchResult(BaseModel):
    """Single result returned by Exa API."""
    title: str
    url: str
    snippet: str
    score: float = 0.0          # original exa score
    rerank_score: float = 0.0   # cross-encoder score (populated after re-ranking)

    class Config:
        arbitrary_types_allowed = True


# ---------------------------------------------------------------------------
# Document / Chunk Layer
# ---------------------------------------------------------------------------

class DocumentChunk(BaseModel):
    """A tokenised slice of a scraped web page."""
    chunk_id: str
    source_url: str
    source_title: str
    text: str
    token_count: int
    embedding: Optional[list[float]] = Field(default=None, exclude=True)


# ---------------------------------------------------------------------------
# Critic feedback
# ---------------------------------------------------------------------------

class CriticFeedback(BaseModel):
    """Structured critique produced by the Critic Agent."""
    factual_correctness_score: float = Field(
        ge=0.0, le=1.0, description="Probability the answer is factually correct."
    )
    completeness_score: float = Field(
        ge=0.0, le=1.0, description="How completely the answer addresses the query."
    )
    hallucination_risk: float = Field(
        ge=0.0, le=1.0, description="Estimated risk that answer contains hallucinations."
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Key facts or aspects that are absent from the draft.",
    )
    improvement_suggestions: list[str] = Field(
        default_factory=list,
        description="Concrete suggestions for the writer to improve the answer.",
    )
    overall_quality: float = Field(
        ge=0.0, le=1.0, description="Aggregate quality score."
    )


# ---------------------------------------------------------------------------
# Agent State (LangGraph TypedDict - supports partial dict merging)
# ---------------------------------------------------------------------------

class PipelineState(TypedDict, total=False):
    """
    Shared state dict passed between LangGraph nodes.
    Using TypedDict so LangGraph can correctly merge partial updates from nodes.
    Every field is optional (total=False) so nodes can be developed independently.
    """
    query: str

    # Stage outputs
    search_results: list[SearchResult]
    reranked_results: list[SearchResult]
    scraped_pages: dict[str, str]           # url -> raw clean text
    chunks: list[DocumentChunk]
    faiss_index_bytes: Optional[bytes]      # serialised FAISS index
    retrieved_chunks: list[DocumentChunk]

    # Writer / Critic loop
    draft_answer: str
    critic_feedback: Optional[CriticFeedback]
    refinement_iteration: int

    # Final
    final_answer: str
    sources: list[str]
    confidence: float

    # Metadata
    pipeline_start_ts: float
    errors: list[str]


# ---------------------------------------------------------------------------
# API Request / Response
# ---------------------------------------------------------------------------

class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500, description="Research question.")
    search_top_n: Optional[int] = Field(default=None, ge=1, le=20)
    reranker_top_k: Optional[int] = Field(default=None, ge=1, le=10)
    retriever_top_k: Optional[int] = Field(default=None, ge=1, le=20)
    refinement_iterations: Optional[int] = Field(default=None, ge=0, le=3)


class SourceDetail(BaseModel):
    url: str
    title: str
    domain: str


class ResearchResponse(BaseModel):
    answer: str
    sources: list[str]
    source_details: list[SourceDetail] = []
    confidence: float
    critic_feedback: Optional[CriticFeedback] = None
    refinement_iterations_run: int = 0
    elapsed_seconds: float = 0.0
    pipeline_errors: list[str] = []


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
