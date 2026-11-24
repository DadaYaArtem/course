# Развёртывание и фоновая обработка PDF

Для демонстрационного стенда нужны Docker с Compose v2, Node.js 24 с npm,
доступ к образам и пакетам и ключ Gemini для ответов на вопросы. Индексация PDF
и проверка готовности Neo4j выполняются без обращения к Gemini.

## Запуск из корня репозитория

1. Скопируйте `.env.example` в `.env`. Задайте `DOCUMENT_PARSER_ENABLED=true`,
   свой `GEMINI_API_KEY` и модель `GEMINI_MODEL`, доступную для этого ключа.
2. Запустите API, исполнитель очереди и Neo4j.

   ```powershell
   docker compose up -d --build neo4j backend document-worker
   docker compose ps
   ```

3. В чистой базе примените ограничения и начальное наполнение. Команды
   используют демонстрационные реквизиты из Compose.

   ```powershell
   docker compose exec neo4j cypher-shell -u neo4j -p password123 -f /cypher/constraints.cypher
   docker compose exec neo4j cypher-shell -u neo4j -p password123 -f /cypher/seed.cypher
   Invoke-RestMethod http://localhost:8000/health
   Invoke-RestMethod http://localhost:8000/ready
   ```

4. В отдельном терминале запустите интерфейс.

   ```powershell
   Set-Location rag-ui
   npm ci
   npm run dev
   ```

   Откройте адрес, указанный Vite. В чистом графе ожидаются 25 узлов и 28
   связей. Проверьте ответ на «Что такое BERT?» и загрузите один из
   тематических PDF из `neo4j/parser_service/parser/samples/corpus_pdfs`.
   Интерфейс покажет состояние задания и обновит список источников после
   завершения импорта. Время появления статуса зависит от опроса API.

## Контракт и диагностика

| Запрос | Результат |
|---|---|
| `GET /health` | HTTP 200, процесс FastAPI отвечает |
| `GET /ready` | HTTP 200 после контрольного чтения Neo4j или HTTP 503 при недоступности БД |
| `POST /document-jobs` | Multipart-поле `file`, HTTP 202 и заголовок `Location` после записи файла и задания |
| `GET /document-jobs/{id}` | Состояние, число попыток и причина ошибки. Для неизвестного UUID — HTTP 404 |
| `POST /document-jobs/{id}/retry` | HTTP 202 для ошибочного задания с доступной попыткой, HTTP 409 для остальных состояний, HTTP 404 для неизвестного UUID |

Первоначально задание получает статус `queued`, при запуске парсера —
`running`, после него — `completed` или `failed`. Действующий маршрут
`POST /documents/upload` по-прежнему выполняет синхронную загрузку.
Состояние `completed` отражает успешное завершение процесса парсера.
Содержимое графа и качество извлечения проверяются отдельно.

Для прямой проверки через API откройте `http://localhost:8000/docs`,
выполните `POST /document-jobs` и используйте возвращённый UUID в
`GET /document-jobs/{id}`. При формате PDF с ошибкой разбора задача может
быть принята, а затем получить статус `failed`. Запросы без PDF-заголовка
отклоняются сразу. Настройки — до 25 МиБ на PDF, до 120 с на попытку и
до 3 попыток включительно. Их задают параметры `DOCUMENT_JOB_MAX_BYTES`,
`DOCUMENT_JOB_TIMEOUT_SECONDS` и `DOCUMENT_JOB_MAX_ATTEMPTS`.

SQLite и PDF находятся на общем томе `backend_uploads`. В нормальном
запуске только один исполнитель держит блокировку очереди. После
перезапуска ожидавшие задания сохраняются, прерванные помечаются как
`failed`. Перед явным повтором после сбоя проверьте граф: предыдущий
запуск мог частично записать данные. Повтор использует тот же PDF.
Для проверки журналов и состояния выполните:

```powershell
docker compose logs --tail 80 neo4j backend document-worker
docker compose restart document-worker
```

`/ready` проверяет Neo4j. Состояние исполнителя контролируется через
`docker compose ps` и контрольное задание, Gemini — контрольным вопросом.
Обычная остановка сохраняет тома. Для переноса или резервного копирования
останавливайте запись и сохраняйте вместе тома `neo4j_data` и
`backend_uploads`, а также каталог результатов парсера.

## Локальная проверка

Из каталога `backend` в окружении с установленным `requirements.txt`
выполните команды. Здесь Neo4j и действительный ключ не требуются.

```powershell
$env:NEO4J_URI = 'bolt://127.0.0.1:7687'
$env:NEO4J_USER = 'neo4j'
$env:NEO4J_PASSWORD = 'test-password'
$env:GEMINI_API_KEY = 'test-key'
python -m pytest -q tests/test_document_jobs.py
```
