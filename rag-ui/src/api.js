const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("json")) {
    return response.json();
  }

  return response.text();
}


function buildApiError(response, data) {
  const error = new Error(
    data?.detail || data?.title || "Ошибка запроса к backend"
  );

  error.status = response.status;
  error.data = data;

  return error;
}

export async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);
  const data = await parseResponse(response);

  if (!response.ok) {
    throw buildApiError(response, data);
  }

  return data;
}

export async function sendQuery({ text, language }) {
  const response = await fetch(`${API_BASE_URL}/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      text,
      language,
    }),
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw buildApiError(response, data);
  }

  return data;
}

export async function getDocuments() {
  const response = await fetch(`${API_BASE_URL}/documents`);
  const data = await parseResponse(response);

  if (!response.ok) {
    throw buildApiError(response, data);
  }

  return data;
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    body: formData,
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    throw buildApiError(response, data);
  }

  return data;
}