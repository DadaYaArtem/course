# RAG Backend — Project Context

## Project Overview
This is the **backend service** for a university RAG system (knowledge base on AI technologies).
The system consists of 3 independent parts developed by different team members:
- **Knowledge Base (done):** Neo4j graph DB populated by a parser pipeline (see `docs/kb_schema.md`)
- **Backend (this repo):** FastAPI service — your responsibility
- **Frontend (separate repo):** Chat UI consuming this API

## Knowledge Base Schema
Neo4j graph, bolt://localhost:7687

**Node labels:** `Concept`, `Model`, `Task`, `Method`, `Framework`

**Node properties:** `name`, `normalized_name`, `aliases[]`, `source`, `description`

**Relationship types:** `IS_A`, `USES`, `USED_FOR`, `IMPLEMENTED_IN`, `RELATED_TO`

**Relationship properties:** `source`, `evidence`, `confidence`, `rule`

All pre-written Cypher queries are in `docs/queries.cypher`.

## Query Types (must be classified)
- **definition** — "Что такое Transformer?"
- **comparison** — "Чем BERT отличается от GPT?"
- **capabilities** — "Для чего используется LLaMA?"
- **methods** — "Какие методы использует BERT?"
- **recommendation** — "Какой фреймворк выбрать для NLP?"

## LLM
Chose some gemini llm that suits our needs

## Tech Stack
- Python 3.11+
- FastAPI + Uvicorn
- neo4j (official Python driver)
- httpx (async llm calls)
- pydantic v2 (settings + schemas)
- python-dotenv

## Code Standards
- **PEP 8** strictly
- **Type hints** on every function signature
- **Docstrings** in Google style on every public class/function
- **Pydantic models** for all request/response schemas — no raw dicts in API layer
- **Dependency injection** via FastAPI `Depends()`
- **No business logic in routers** — routers call services, services call repositories
- **Async** throughout (async def, AsyncDriver for Neo4j)
- **Structured logging** via `logging` module, not print()
- All secrets via environment variables, never hardcoded
- `.env.example` must be kept up to date

## Architecture (layered)
routers/     → HTTP layer only (validate input, call service, return response)
services/    → business logic (classify query, build prompt, call LLM)
repositories/→ data access only (Neo4j queries)
schemas/     → Pydantic request/response models
core/        → config, db connection, logging setup

## What to build — see PLAN.md