# Backend Development Plan

## Phase 1 — Project Skeleton
- [ ] Project structure (folders: routers, services, repositories, schemas, core)
- [ ] `core/config.py` — Settings via pydantic-settings (NEO4J_*, APP_*)
- [ ] `core/database.py` — async Neo4j driver, lifespan dependency
- [ ] `core/logging.py` — structured logging setup
- [ ] `main.py` — FastAPI app, lifespan, CORS, health check GET /health
- [ ] `requirements.txt` + `.env.example`

## Phase 2 — Neo4j Repository Layer
- [ ] `repositories/graph_repository.py`
  - `find_entity(term)` → Q1
  - `search_entities(q)` → Q2
  - `get_definition(concept)` → Q3
  - `get_neighbors(name)` → Q4
  - `get_model_tasks(model)` → Q5
  - `get_model_methods(model)` → Q6
  - `compare_models(a, b)` → Q8
  - `entity_exists(name)` → Q9
- [ ] Manual integration test against real Neo4j (pytest, not mocked)

## Phase 3 — Query Classifier
- [ ] `services/classifier.py`
  - Rule-based classifier (keyword matching + regex)
  - Input: raw user text → Output: QueryType enum + extracted entities
  - Cover all 5 query types
  - Unit tests in `tests/test_classifier.py`

## Phase 4 — Prompt Builder
- [ ] `services/prompt_builder.py`
  - Builds prompt string from query type + Neo4j context dict
  - Each query type has its own prompt template
  - If context is empty → returns fallback prompt with warning flag
  - Unit tests with mock context

## Phase 5 — LLM Client
- [ ] `services/llm_client.py`
  - Async httpx client for llm `/api/generate`
  - Streaming support (optional for MVP)
  - Timeout + retry logic
  - Returns: generated text + latency

## Phase 6 — Query Service (orchestrator)
- [ ] `services/query_service.py`
  - Combines classifier → repository → prompt_builder → llm_client
  - Returns structured result: answer, source_entities, query_type, from_kb (bool)

## Phase 7 — API Endpoints
- [ ] `routers/query.py`
  - `POST /query` — main chat endpoint
  - Request: `{ "text": str, "language": "ru"|"en" }`
  - Response: `{ "answer": str, "query_type": str, "source_entities": [...], "from_kb": bool }`
- [ ] `routers/documents.py`
  - `POST /documents/upload` — accept PDF, trigger parser pipeline
  - `GET /documents` — list indexed sources

## Phase 8 — Error Handling & Validation
- [ ] Global exception handler (FastAPI middleware)
- [ ] Custom exceptions: `EntityNotFoundError`, `Neo4jConnectionError`, `LLMError`
- [ ] HTTP error responses follow RFC 7807 (Problem Details)

## Phase 9 — Testing
- [ ] `tests/test_classifier.py` — unit
- [ ] `tests/test_prompt_builder.py` — unit  
- [ ] `tests/test_query_service.py` — integration (real Neo4j + mocked LLM)
- [ ] `tests/test_api.py` — e2e with TestClient

## Phase 10 — Docker & Docs
- [ ] `Dockerfile` for backend service
- [ ] `docker-compose.yml` (backend + neo4j + ollama)
- [ ] `README.md` — setup, env vars, API reference