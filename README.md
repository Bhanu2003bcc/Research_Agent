# Multi-Agent Research System

A **production-grade**, 10-stage multi-agent research pipeline that takes a natural language query and returns a high-quality, fact-grounded, self-refined answer with citations — powered by real-time web data.

---

## Architecture Overview

```
Research Query
      │
      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          LangGraph Pipeline                          │
│                                                                      │
│  [1] Search Agent ──────────────────────────► Exa API (Live)        │
│         │                                                            │
│         ▼                                                            │
│  [2] Re-Ranker  (cross-encoder/ms-marco-MiniLM-L-6-v2)              │
│         │                                                            │
│         ▼                                                            │
│  [3] Reader Agent ─────────────────────────► BeautifulSoup Scraper  │
│         │                                                            │
│         ▼                                                            │
│  [4] Chunker  (500–1000 token chunks, overlapping)                  │
│         │                                                            │
│         ▼                                                            │
│  [5] Embedder  (all-MiniLM-L6-v2 → FAISS IndexFlatIP)               │
│         │                                                            │
│         ▼                                                            │
│  [6] Retriever  (FAISS cosine search, top-K)                        │
│         │                                                            │
│         ▼                                                            │
│  [7] Writer Agent  (GPT-4o-mini + citations)  ◄──────────┐          │
│         │                                                 │ refine   │
│         ▼                                                 │          │
│  [8] Critic Agent  → structured CriticFeedback JSON      │          │
│         │                                                 │          │
│         └──── quality < threshold? ───────────────────── ┘          │
│                                                                      │
│  [9] Refinement Loop (configurable max iterations)                  │
│                                                                      │
│  [10] Finalizer → { answer, sources, confidence }                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph (StateGraph) |
| LLM | GPT-4o-mini via LangChain |
| Search | Exa API (`exa-py`) |
| Scraper | aiohttp + BeautifulSoup4 |
| Re-Ranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Embeddings | `all-MiniLM-L6-v2` (sentence-transformers) |
| Vector Index | FAISS (IndexFlatIP, cosine similarity) |
| API Framework | FastAPI + Uvicorn |
| Logging | structlog (JSON) |

---

## Project Structure

```
multi_agent_research/
├── agents/
│   ├── search_agent.py       # Node 1: Exa API search
│   ├── reranker.py           # Node 2: Cross-encoder re-ranking
│   ├── reader_agent.py       # Node 3: Async URL scraping
│   ├── chunker.py            # Node 4: Token-bounded chunking
│   ├── embedder.py           # Node 5: Embedding + FAISS indexing
│   ├── retriever.py          # Node 6: FAISS retrieval
│   ├── writer_agent.py       # Node 7: LLM synthesis with citations
│   ├── critic_agent.py       # Node 8: Structured quality evaluation
│   └── finalizer.py          # Node 10: Output assembly
├── core/
│   ├── config.py             # Pydantic Settings
│   ├── models.py             # All Pydantic data models
│   ├── logging.py            # structlog setup
│   └── pipeline.py           # LangGraph graph definition + refinement loop
├── tools/
│   ├── exa_search.py         # Exa API wrapper (Tool 1)
│   └── bs4_scraper.py        # BeautifulSoup scraper (Tool 2)
├── api/
│   └── app.py                # FastAPI application
├── main.py                   # Uvicorn entrypoint
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
# EXA_API_KEY is already set
```

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the server

```bash
python main.py
# API available at http://localhost:8000
# Swagger UI at http://localhost:8000/docs
```

### 4. Or use Docker

```bash
docker-compose up --build
```

---

## API Usage

### POST `/research`

**Request:**
```json
{
  "query": "What are the latest breakthroughs in quantum computing in 2025?",
  "search_top_n": 10,
  "reranker_top_k": 5,
  "retriever_top_k": 8,
  "refinement_iterations": 2
}
```

**Response:**
```json
{
  "answer": "## Quantum Computing Breakthroughs in 2025\n\nRecent research has demonstrated... [Source: https://example.com/article]",
  "sources": [
    "https://example.com/quantum-2025",
    "https://nature.com/quantum-breakthroughs"
  ],
  "confidence": 0.847,
  "critic_feedback": {
    "factual_correctness_score": 0.91,
    "completeness_score": 0.85,
    "hallucination_risk": 0.12,
    "missing_information": [],
    "improvement_suggestions": [],
    "overall_quality": 0.88
  },
  "refinement_iterations_run": 1,
  "elapsed_seconds": 24.5,
  "pipeline_errors": []
}
```

### GET `/health`

```json
{ "status": "ok", "version": "1.0.0" }
```

---

## Configuration

All settings are in `.env` (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `EXA_API_KEY` | provided | Exa API key |
| `OPENAI_API_KEY` | required | OpenAI API key |
| `SEARCH_TOP_N` | `10` | Number of Exa search results |
| `RERANKER_TOP_K` | `5` | Results kept after re-ranking |
| `READER_TIMEOUT_SECONDS` | `10` | Per-URL scrape timeout |
| `READER_MAX_CONCURRENT` | `5` | Concurrent scrape connections |
| `CHUNK_SIZE_TOKENS` | `750` | Target tokens per chunk |
| `CHUNK_OVERLAP_TOKENS` | `100` | Token overlap between chunks |
| `RETRIEVER_TOP_K` | `8` | Chunks returned from FAISS |
| `REFINEMENT_MAX_ITERATIONS` | `2` | Max writer–critic loops |
| `LLM_MODEL` | `gpt-4o-mini` | OpenAI model |
| `PORT` | `8000` | Server port |

---

## Pipeline Details

### Refinement Loop
The Writer ↔ Critic loop runs until either:
- `refinement_iteration >= REFINEMENT_MAX_ITERATIONS`, or
- `critic_feedback.overall_quality >= 0.88` (early exit)

### Confidence Score Formula
```
confidence = 0.35 × factual_correctness
           + 0.30 × completeness
           + 0.20 × (1 - hallucination_risk)
           + 0.15 × overall_quality
```

### Scraper Robustness
- Skips 403/404/410/451 responses gracefully
- Charset auto-detection via `chardet`
- Strips nav/footer/ads/scripts/comments via CSS class heuristics
- Prefers `<article>` / `<main>` content areas

---

## License
MIT
