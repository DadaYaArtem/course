import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

import {
  checkHealth,
  createDocumentJob,
  getDocumentJob,
  getDocuments,
  sendQuery,
} from "./api";

import "./App.css";



const examples = [
  {
    label: "Определение",
    text: "Что такое Transformer?",
    language: "ru",
  },
  {
    label: "Сравнение",
    text: "Чем BERT отличается от GPT?",
    language: "ru",
  },
  {
    label: "Возможности",
    text: "Для чего используется BERT?",
    language: "ru",
  },
  {
    label: "Методы",
    text: "What methods does GPT use?",
    language: "ru",
  },
  {
    label: "Рекомендация",
    text: "Какой инструмент выбрать для NLP?",
    language: "ru",
  },
];





function App() {
  const [text, setText] = useState("Что такое Transformer?");
  const [language, setLanguage] = useState("ru");

  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const [healthStatus, setHealthStatus] = useState("checking");
  const [healthError, setHealthError] = useState(null);

  const [documents, setDocuments] = useState([]);
  const [documentsError, setDocumentsError] = useState(null);
  const [isDocumentsLoading, setIsDocumentsLoading] = useState(false);

  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadMessage, setUploadMessage] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [activeJobId, setActiveJobId] = useState(() =>
    localStorage.getItem("rag_active_document_job")
  );

  const [history, setHistory] = useState(() => {
    const savedHistory = localStorage.getItem("rag_query_history");
    return savedHistory ? JSON.parse(savedHistory) : [];
  });

  useEffect(() => {
    loadHealth();
    loadDocuments();
  }, []);

  useEffect(() => {
    if (!activeJobId) return;
    const controller = new AbortController();
    let timer;

    function finishJob() {
      localStorage.removeItem("rag_active_document_job");
      setActiveJobId(null);
    }

    async function pollJob() {
      try {
        const job = await getDocumentJob(activeJobId, controller.signal);
        if (controller.signal.aborted) return;
        if (job.status === "completed") {
          setUploadMessage(`${job.filename}: PDF обработан и импортирован в Neo4j.`);
          finishJob();
          await loadDocuments();
          return;
        }
        if (job.status === "failed") {
          setUploadMessage(null);
          setUploadError(`${job.filename}: обработка завершилась ошибкой. Задание ${job.id}.`);
          finishJob();
          return;
        }
        setUploadMessage(
          job.status === "running" ? `${job.filename}: обрабатывается.` : `${job.filename}: в очереди.`
        );
      } catch (error) {
        if (controller.signal.aborted) return;
        if (error.status === 404) {
          setUploadMessage(null);
          setUploadError("Задание не найдено.");
          finishJob();
          return;
        }
        setUploadMessage("Не удалось проверить статус. Повторяем запрос…");
      }
      timer = setTimeout(pollJob, 1500);
    }

    pollJob();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [activeJobId]);

  async function loadHealth() {
    setHealthStatus("checking");
    setHealthError(null);

    try {
      await checkHealth();
      setHealthStatus("ok");
    } catch (requestError) {
      setHealthStatus("error");
      setHealthError(
        requestError.data?.detail ||
          requestError.data?.title ||
          requestError.message ||
          "Backend недоступен"
      );
    }
  }

  async function loadDocuments() {
    setIsDocumentsLoading(true);
    setDocumentsError(null);

    try {
      const data = await getDocuments();
      setDocuments(Array.isArray(data) ? data : []);
    } catch (requestError) {
      setDocumentsError(
        requestError.data?.detail ||
          requestError.data?.title ||
          requestError.message ||
          "Не удалось загрузить список документов"
      );
    } finally {
      setIsDocumentsLoading(false);
    }
  }

  function saveHistoryItem(queryText, queryLanguage, responseData) {
    const historyItem = {
      id: Date.now(),
      text: queryText,
      language: queryLanguage,
      queryType: responseData.query_type,
      entities: responseData.source_entities || [],
      answer: responseData.answer,
      fromKb: responseData.from_kb,
      classificationSource: responseData.classification_source,
      createdAt: new Date().toLocaleString(),
    };

    const updatedHistory = [historyItem, ...history].slice(0, 10);

    setHistory(updatedHistory);
    localStorage.setItem("rag_query_history", JSON.stringify(updatedHistory));
  }

  function clearHistory() {
    setHistory([]);
    localStorage.removeItem("rag_query_history");
  }

  function applyHistoryItem(item) {
    setText(item.text);
    setLanguage(item.language);
    setError(null);
    setResult({
      answer: item.answer,
      query_type: item.queryType,
      source_entities: item.entities,
      from_kb: item.fromKb,
      classification_source: item.classificationSource,
    });
  }

  function applyExample(example) {
    setText(example.text);
    setLanguage(example.language);
    setError(null);
    setResult(null);
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const normalizedText = text.trim();

    if (!normalizedText) {
      setError({
        title: "Пустой запрос",
        detail: "Введите текст запроса перед отправкой.",
      });
      setResult(null);
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await sendQuery({
        text: normalizedText,
        language,
      });

      setResult(data);
      saveHistoryItem(normalizedText, language, data);
    } catch (requestError) {
      setError({
        title: requestError.data?.title || "Ошибка backend",
        detail:
          requestError.data?.detail ||
          requestError.message ||
          "Не удалось получить ответ от backend.",
        status: requestError.status,
      });
    } finally {
      setIsLoading(false);
    }
  }

  async function handleUpload(event) {
    event.preventDefault();

    if (!selectedFile) {
      setUploadError("Выберите PDF-файл перед загрузкой.");
      setUploadMessage(null);
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    setUploadMessage(null);

    try {
      const job = await createDocumentJob(selectedFile);
      localStorage.setItem("rag_active_document_job", job.id);
      setActiveJobId(job.id);
      setUploadMessage(`${job.filename}: принят в очередь.`);

      setSelectedFile(null);
      event.target.reset();

    } catch (requestError) {
      setUploadError(
        requestError.data?.detail ||
          requestError.data?.title ||
          requestError.message ||
          "Не удалось загрузить документ."
      );
    } finally {
      setIsUploading(false);
    }
  }

  const classificationLabel =
    result?.classification_source === "llm"
      ? "LLM"
      : result?.classification_source === "rules"
        ? "Rules fallback"
        : "не указан";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">AI</div>

          <div>
            <h1>RAG-справочник по ИИ</h1>
            <p>База знаний по технологиям искусственного интеллекта</p>
          </div>
        </div>

        <section className="side-card status-card">
          <div className="side-card-header">
            <span>Backend</span>

            {healthStatus === "checking" && (
              <span className="status-badge checking">проверка</span>
            )}

            {healthStatus === "ok" && (
              <span className="status-badge ok">работает</span>
            )}

            {healthStatus === "error" && (
              <span className="status-badge bad">ошибка</span>
            )}
          </div>

          <button type="button" className="secondary-button" onClick={loadHealth}>
            Проверить статус
          </button>

          {healthError && <p className="side-error">{healthError}</p>}
        </section>

        <section className="side-card history-card">
          <div className="side-card-header">
            <span>История</span>

            {history.length > 0 && (
              <button type="button" className="text-button" onClick={clearHistory}>
                Очистить
              </button>
            )}
          </div>

          {history.length === 0 && (
            <p className="muted">История запросов пока пустая.</p>
          )}

          {history.length > 0 && (
            <div className="history-list">
              {history.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className="history-item"
                  onClick={() => applyHistoryItem(item)}
                >
                  <span>{item.text}</span>
                  <small>
                    {item.queryType || "unknown"} ·{" "}
                    {item.classificationSource === "llm"
                      ? "LLM"
                      : item.classificationSource === "rules"
                        ? "Rules"
                        : "—"}
                    {item.createdAt ? ` · ${item.createdAt}` : ""}
                  </small>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="side-card documents-card">
          <div className="side-card-header">
            <span>Источники</span>

            <button
              type="button"
              className="text-button"
              onClick={loadDocuments}
              disabled={isDocumentsLoading}
            >
              {isDocumentsLoading ? "..." : "Обновить"}
            </button>
          </div>

          {documentsError && <p className="side-error">{documentsError}</p>}

          {!documentsError && documents.length === 0 && (
            <p className="muted">Источники не найдены.</p>
          )}

          {documents.length > 0 && (
            <ul className="documents-list">
              {documents.map((documentItem, index) => (
                <li key={`${documentItem.source || "source"}-${index}`}>
                  {documentItem.source || JSON.stringify(documentItem)}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="side-card upload-card">
          <div className="side-card-header">
            <span>Загрузка PDF</span>
          </div>

          <form onSubmit={handleUpload} className="upload-form">
            <label htmlFor="pdfUpload" className="file-picker">
              <span className="file-picker-button">Выбрать PDF</span>
              <span className="file-picker-name">
                {selectedFile ? selectedFile.name : "Файл не выбран"}
              </span>
            </label>

            <input
              id="pdfUpload"
              className="hidden-file-input"
              type="file"
              accept="application/pdf,.pdf"
              onChange={(event) => {
                setSelectedFile(event.target.files?.[0] || null);
                setUploadError(null);
                setUploadMessage(null);
              }}
            />

            <button type="submit" disabled={isUploading || Boolean(activeJobId)}>
              {isUploading ? "Загрузка..." : "Загрузить"}
            </button>
          </form>

          {uploadMessage && (
            <div className="upload-result success" role="status">
              <p>{uploadMessage}</p>
            </div>
          )}

          {uploadError && <p className="side-error">{uploadError}</p>}
        </section>
      </aside>

      <main className="chat-area">
        <header className="chat-header">
          <div>
            <h2>Диалог с RAG-системой</h2>
            <p>
              Введите вопрос, система определит тип запроса, найдёт сущности и
              сформирует ответ на основе базы знаний.
            </p>
          </div>

          <div className="stack-badge">React · FastAPI · Neo4j</div>
        </header>

        <section className="examples-bar">
          {examples.map((example) => (
            <button
              key={example.label}
              type="button"
              onClick={() => applyExample(example)}
            >
              {example.label}
            </button>
          ))}
        </section>

        <section className="conversation">
          <div className="message user-message">
            <div className="avatar">Вы</div>

            <div className="bubble">
              <span className="bubble-label">Запрос пользователя</span>
              <p>{text.trim() || "Введите запрос..."}</p>
            </div>
          </div>

          {isLoading && (
            <div className="message assistant-message">
              <div className="avatar assistant-avatar">AI</div>

              <div className="bubble assistant-bubble">
                <span className="bubble-label">Система</span>
                <p>Обрабатываю запрос, выполняю классификацию и поиск в БЗ...</p>
              </div>
            </div>
          )}

          {error && (
            <div className="message assistant-message">
              <div className="avatar assistant-avatar error-avatar">!</div>

              <div className="bubble error-bubble">
                <span className="bubble-label">{error.title}</span>
                <p>{error.detail}</p>

                {error.status && <small>HTTP status: {error.status}</small>}
              </div>
            </div>
          )}

          {result && (
            <div className="message assistant-message">
              <div className="avatar assistant-avatar">AI</div>

              <div className="bubble assistant-bubble">
                <div className="answer-header">
                  <span className="bubble-label">Ответ системы</span>

                  <span className={result.from_kb ? "kb-label ok" : "kb-label bad"}>
                    {result.from_kb
                      ? "Ответ из базы знаний"
                      : "Контекста в БЗ не хватило"}
                  </span>
                </div>

                <div className="meta-grid">
                  <div>
                    <strong>Тип запроса</strong>
                    <span>{result.query_type || "unknown"}</span>
                  </div>

                  <div>
                    <strong>Сущности</strong>
                    <span>
                      {result.source_entities?.length
                        ? result.source_entities.join(", ")
                        : "не найдены"}
                    </span>
                  </div>

                  <div>
                    <strong>Классификация</strong>
                    <span>{classificationLabel}</span>
                  </div>
                </div>

                <div className="markdown-answer">
                  <ReactMarkdown>
                    {String(result.answer || "").trim()}
                  </ReactMarkdown>
                </div>

                <details className="json-details">
                  <summary>Полный JSON-ответ backend</summary>
                  <pre>{JSON.stringify(result, null, 2)}</pre>
                </details>
              </div>
            </div>
          )}
        </section>

        <form onSubmit={handleSubmit} className="composer">
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();

                if (!isLoading) {
                  event.currentTarget.form?.requestSubmit();
                }
              }
            }}
            placeholder="Введите вопрос по технологиям ИИ..."
          />

          <div className="composer-footer">
            <select
              value={language}
              onChange={(event) => setLanguage(event.target.value)}
            >
              <option value="ru">Русский</option>
              <option value="en">English</option>
            </select>

            <button type="submit" disabled={isLoading}>
              {isLoading ? "Обработка..." : "Отправить"}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}

export default App;
