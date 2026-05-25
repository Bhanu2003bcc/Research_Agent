"""
api/app.py
FastAPI application – exposes the multi-agent pipeline as a REST API.
"""
from __future__ import annotations
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from core.config import get_settings
from core.logging import get_logger, setup_logging
from core.models import (
    HealthResponse,
    ResearchRequest,
    ResearchResponse,
)
from core.pipeline import compile_pipeline

logger = get_logger(__name__)
_pipeline = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: compile the pipeline graph once."""
    global _pipeline
    setup_logging()
    logger.info("pipeline_compiling")
    _pipeline = compile_pipeline()
    logger.info("pipeline_ready")
    yield
    logger.info("shutdown")


app = FastAPI(
    title="Multi-Agent Research API",
    description=(
        "Production-grade multi-agent research pipeline powered by "
        "Exa API, BeautifulSoup, sentence-transformers, FAISS, and LangGraph."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["root"])
async def root():
    """Serve the frontend UI."""
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path, media_type="text/html")
    return RedirectResponse(url="/docs")


@app.get("/favicon.ico", tags=["root"])
async def favicon():
    """Suppress favicon 404 errors."""
    return JSONResponse(status_code=204, content={})


@app.get("/health", response_model=HealthResponse, tags=["ops"])
async def health():
    return HealthResponse()


@app.post("/research", response_model=ResearchResponse, tags=["research"])
async def research(req: ResearchRequest):
    """
    Run the full multi-agent research pipeline for a given query.

    The pipeline:
    1. Search Agent   – Exa API real-time results
    2. Re-Ranker      – Cross-encoder semantic scoring
    3. Reader Agent   – BeautifulSoup async scraper
    4. Chunker        – Token-bounded text splitting
    5. Embedder       – sentence-transformers + FAISS indexing
    6. Retriever      – FAISS nearest-neighbour search
    7. Writer Agent   – LLM synthesis with citations
    8. Critic Agent   – Structured quality evaluation
    9. Refinement     – Iterative improvement loop
    10. Final Output  – JSON with answer, sources, confidence
    """
    global _pipeline
    if _pipeline is None:
        raise HTTPException(503, "Pipeline not ready")

    settings = get_settings()
    t0 = time.time()

    # Build initial state as plain dict (TypedDict compatible)
    initial_state: dict = {
        "query": req.query,
        "search_results": [],
        "reranked_results": [],
        "scraped_pages": {},
        "chunks": [],
        "faiss_index_bytes": None,
        "retrieved_chunks": [],
        "draft_answer": "",
        "critic_feedback": None,
        "refinement_iteration": 0,
        "final_answer": "",
        "sources": [],
        "confidence": 0.0,
        "pipeline_start_ts": t0,
        "errors": [],
    }

    # Override defaults from request if provided
    # (Config override is done per-request via monkey-patching on settings)
    _orig_search_n = settings.search_top_n
    _orig_rerank_k = settings.reranker_top_k
    _orig_ret_k    = settings.retriever_top_k
    _orig_ref_iter = settings.refinement_max_iterations

    if req.search_top_n is not None:
        settings.search_top_n = req.search_top_n
    if req.reranker_top_k is not None:
        settings.reranker_top_k = req.reranker_top_k
    if req.retriever_top_k is not None:
        settings.retriever_top_k = req.retriever_top_k
    if req.refinement_iterations is not None:
        settings.refinement_max_iterations = req.refinement_iterations

    try:
        logger.info("pipeline_invoke_start", query=req.query)
        final_state: dict = await _pipeline.ainvoke(initial_state)
        logger.info("pipeline_invoke_done", query=req.query)
    except Exception as exc:
        logger.error("pipeline_invoke_failed", error=str(exc))
        raise HTTPException(500, f"Pipeline execution failed: {exc}") from exc
    finally:
        # Restore original settings
        settings.search_top_n        = _orig_search_n
        settings.reranker_top_k      = _orig_rerank_k
        settings.retriever_top_k     = _orig_ret_k
        settings.refinement_max_iterations = _orig_ref_iter

    elapsed = round(time.time() - t0, 2)

    return ResearchResponse(
        answer=final_state.get("final_answer", ""),
        sources=final_state.get("sources", []),
        confidence=final_state.get("confidence", 0.0),
        critic_feedback=final_state.get("critic_feedback"),
        refinement_iterations_run=final_state.get("refinement_iteration", 0),
        elapsed_seconds=elapsed,
        pipeline_errors=final_state.get("errors", []),
    )


# ---------------------------------------------------------------------------
# Frontend Static Files
# ---------------------------------------------------------------------------

@app.get("/styles.css", include_in_schema=False)
async def get_styles():
    """Serve frontend CSS."""
    css_file = Path(__file__).parent.parent / "frontend" / "styles.css"
    if css_file.exists():
        return FileResponse(css_file, media_type="text/css")
    return JSONResponse({"error": "Stylesheet not found"}, status_code=404)


@app.get("/script.js", include_in_schema=False)
async def get_script():
    """Serve frontend JavaScript."""
    js_file = Path(__file__).parent.parent / "frontend" / "script.js"
    if js_file.exists():
        return FileResponse(js_file, media_type="application/javascript")
    return JSONResponse({"error": "Script not found"}, status_code=404)
