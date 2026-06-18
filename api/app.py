"""
api/app.py
FastAPI application – exposes the multi-agent pipeline as a REST API.
"""
from __future__ import annotations
import time
import json
from urllib.parse import urlparse
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, StreamingResponse
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

    # Build source details with title and domain mapping
    reranked = final_state.get("reranked_results", [])
    retrieved = final_state.get("retrieved_chunks", [])
    
    url_to_title = {}
    for r in reranked:
        if r.url and r.title:
            url_to_title[r.url] = r.title
    for c in retrieved:
        if c.source_url and c.source_title:
            url_to_title[c.source_url] = c.source_title

    source_details = []
    for url in final_state.get("sources", []):
        title = url_to_title.get(url, "")
        if not title:
            parsed = urlparse(url)
            title = parsed.path.strip("/").split("/")[-1] or parsed.netloc
            title = title.replace("-", " ").replace("_", " ").title()[:60] or "Source Link"
        
        parsed = urlparse(url)
        domain = parsed.netloc
        source_details.append({
            "url": url,
            "title": title,
            "domain": domain
        })

    return ResearchResponse(
        answer=final_state.get("final_answer", ""),
        sources=final_state.get("sources", []),
        source_details=source_details,
        confidence=final_state.get("confidence", 0.0),
        critic_feedback=final_state.get("critic_feedback"),
        refinement_iterations_run=final_state.get("refinement_iteration", 0),
        elapsed_seconds=elapsed,
        pipeline_errors=final_state.get("errors", []),
    )


@app.post("/research/stream", tags=["research"])
async def research_stream(req: ResearchRequest):
    """
    Stream events and updates during the research pipeline execution using SSE.
    """
    global _pipeline
    if _pipeline is None:
        raise HTTPException(503, "Pipeline not ready")

    async def event_generator():
        settings = get_settings()
        t0 = time.time()
        
        # Override defaults
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

        try:
            logger.info("pipeline_stream_invoke_start", query=req.query)
            yield f"data: {json.dumps({'event': 'start', 'message': 'Initializing research pipeline...'})}\n\n"
            
            accumulated_state = dict(initial_state)

            async for event in _pipeline.astream(initial_state):
                for node_name, node_output in event.items():
                    accumulated_state.update(node_output)
                    
                    message = ""
                    details = {}
                    
                    if node_name == "search":
                        count = len(node_output.get("search_results", []))
                        message = f"Search Agent: Retrieved {count} real-time web results."
                        details = {"count": count}
                    elif node_name == "rerank":
                        count = len(node_output.get("reranked_results", []))
                        message = f"Re-Ranker: Screened and kept top {count} most relevant sources."
                        details = {"count": count}
                    elif node_name == "read":
                        scraped = node_output.get("scraped_pages", {})
                        count = sum(1 for text in scraped.values() if text.strip())
                        message = f"Reader Agent: Successfully scraped {count} web pages."
                        details = {"count": count}
                    elif node_name == "chunk":
                        count = len(node_output.get("chunks", []))
                        message = f"Chunker: Partitioned content into {count} text blocks."
                        details = {"count": count}
                    elif node_name == "embed":
                        message = "Embedder: Generated embeddings and built local FAISS index."
                    elif node_name == "retrieve":
                        count = len(node_output.get("retrieved_chunks", []))
                        message = f"Retriever: Extracted top {count} relevant text segments."
                        details = {"count": count}
                    elif node_name == "write":
                        iter_num = accumulated_state.get("refinement_iteration", 0)
                        if iter_num > 0:
                            message = f"Writer Agent (Iteration {iter_num}): Revising draft based on Critic feedback."
                        else:
                            message = "Writer Agent: Synthesizing initial draft answer."
                    elif node_name == "critique":
                        cf = node_output.get("critic_feedback")
                        if cf:
                            message = f"Critic Agent: Evaluated draft quality (Quality: {int(cf.overall_quality * 100)}%, Hallucination Risk: {int(cf.hallucination_risk * 100)}%)."
                            details = {
                                "factual_correctness": cf.factual_correctness_score,
                                "completeness": cf.completeness_score,
                                "hallucination_risk": cf.hallucination_risk,
                                "overall_quality": cf.overall_quality,
                                "missing_information": cf.missing_information,
                                "improvement_suggestions": cf.improvement_suggestions
                            }
                        else:
                            message = "Critic Agent: Evaluated draft."
                    elif node_name == "increment_iter":
                        iter_num = accumulated_state.get("refinement_iteration", 0)
                        message = f"Pipeline: Initiating refinement iteration {iter_num}..."
                    elif node_name == "finalise":
                        message = "Finalizer: Formatting final answer and consolidating sources."

                    yield f"data: {json.dumps({'event': 'progress', 'node': node_name, 'message': message, 'details': details})}\n\n"

            elapsed = round(time.time() - t0, 2)
            
            # Build source details
            reranked = accumulated_state.get("reranked_results", [])
            retrieved = accumulated_state.get("retrieved_chunks", [])
            
            url_to_title = {}
            for r in reranked:
                if r.url and r.title:
                    url_to_title[r.url] = r.title
            for c in retrieved:
                if c.source_url and c.source_title:
                    url_to_title[c.source_url] = c.source_title

            source_details = []
            for url in accumulated_state.get("sources", []):
                title = url_to_title.get(url, "")
                if not title:
                    parsed = urlparse(url)
                    title = parsed.path.strip("/").split("/")[-1] or parsed.netloc
                    title = title.replace("-", " ").replace("_", " ").title()[:60] or "Source Link"
                
                parsed = urlparse(url)
                domain = parsed.netloc
                source_details.append({
                    "url": url,
                    "title": title,
                    "domain": domain
                })

            final_response = {
                "answer": accumulated_state.get("final_answer", ""),
                "sources": accumulated_state.get("sources", []),
                "source_details": source_details,
                "confidence": accumulated_state.get("confidence", 0.0),
                "critic_feedback": accumulated_state.get("critic_feedback").model_dump() if accumulated_state.get("critic_feedback") else None,
                "refinement_iterations_run": accumulated_state.get("refinement_iteration", 0),
                "elapsed_seconds": elapsed,
                "pipeline_errors": accumulated_state.get("errors", []),
            }

            yield f"data: {json.dumps({'event': 'result', 'data': final_response})}\n\n"
            logger.info("pipeline_stream_invoke_done", query=req.query)

        except Exception as exc:
            logger.error("pipeline_stream_invoke_failed", error=str(exc))
            yield f"data: {json.dumps({'event': 'error', 'message': f'Pipeline stream execution failed: {str(exc)}'})}\n\n"
        finally:
            settings.search_top_n        = _orig_search_n
            settings.reranker_top_k      = _orig_rerank_k
            settings.retriever_top_k     = _orig_ret_k
            settings.refinement_max_iterations = _orig_ref_iter

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
