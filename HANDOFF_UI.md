# UI Handoff

Краткая инструкция для разработки UI поверх готового backend API.

## Что внутри проекта

- `backend/` - FastAPI backend RAG-системы.
- `neo4j/cypher/` - constraints и seed-данные для Neo4j.
- `neo4j/parser_service/` - parser pipeline для PDF/текстов.
- `docker-compose.yml` - запуск Neo4j, backend и parser-service.
- `.env` - готовые переменные окружения для Docker Compose.
- `backend/.env` - переменные для локального запуска backend без Docker.
- `test_queries.md` - примеры тестовых запросов и ответов.

## Быстрый запуск через Docker

Из корня проекта:

```powershell
docker compose up -d neo4j backend
```

Загрузить ограничения и seed-граф:

```powershell
docker exec neo4j cypher-shell -u neo4j -p password123 -f /cypher/constraints.cypher
docker exec neo4j cypher-shell -u neo4j -p password123 -f /cypher/seed.cypher
```

Проверить backend:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Swagger/OpenAPI:

```text
http://localhost:8000/docs
```

Neo4j Browser:

```text
http://localhost:7474
```

Логин Neo4j:

```text
user: neo4j
password: password123
```

## Основной endpoint для UI

```http
POST http://localhost:8000/query
Content-Type: application/json
```

Request body:

```json
{
  "text": "What is BERT used for?",
  "language": "en"
}
```

Response:

```json
{
  "answer": "BERT is used for ...",
  "query_type": "capabilities",
  "source_entities": ["BERT"],
  "from_kb": true
}
```

Поля:

- `answer` - финальный ответ LLM.
- `query_type` - тип запроса: `definition`, `comparison`, `capabilities`, `methods`, `recommendation`, `unknown`.
- `source_entities` - сущности, найденные classifier/retriever.
- `from_kb` - `true`, если ответ построен на контексте из Neo4j; `false`, если контекста не хватило.

## Дополнительные endpoints

Список источников в Neo4j:

```http
GET http://localhost:8000/documents
```

Ответ:

```json
[
  {
    "source": "manual_seed"
  }
]
```

Загрузка PDF:

```http
POST http://localhost:8000/documents/upload
Content-Type: multipart/form-data
```

Поле файла:

```text
file
```

Важно: по умолчанию `DOCUMENT_PARSER_ENABLED=false`, поэтому файл сохраняется, но parser pipeline автоматически не запускается.

## Формат ошибок

Ошибки возвращаются в формате Problem Details:

```json
{
  "type": "https://example.com/problems/llm-error",
  "title": "LLM Error",
  "status": 502,
  "detail": "Gemini generation request failed",
  "instance": "/query"
}
```

Для UI достаточно показывать пользователю `title` и `detail`, а `status` использовать для логики.

## CORS

CORS в backend открыт для всех origins, поэтому UI можно запускать на любом локальном порту, например:

```text
http://localhost:3000
http://localhost:5173
```

## Примеры тестовых запросов

```json
{
  "text": "What is BERT used for?",
  "language": "en"
}
```

```json
{
  "text": "Compare BERT and GPT",
  "language": "en"
}
```

```json
{
  "text": "What methods does GPT use?",
  "language": "en"
}
```

```json
{
  "text": "Для чего используется BERT?",
  "language": "ru"
}
```

## Локальный запуск backend без Docker

```powershell
cd backend
py -3.11 -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
$env:PYTHONPATH="."
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Для такого запуска используется `backend/.env`, а не корневой `.env`.

## Тесты backend

Перед integration/e2e тестами должен быть запущен Neo4j и загружен seed.

```powershell
cd backend
$env:PYTHONPATH="."
.\venv\Scripts\python.exe -m pytest -v
```

Ожидаемый результат текущей версии:

```text
62 passed
```

