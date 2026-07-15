const API_BASE_URL = "http://localhost:5000";

export async function extractReceipt(file, documentTypeHint = "auto") {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("document_type_hint", documentTypeHint);

  const response = await fetch(`${API_BASE_URL}/api/extract`, {
    method: "POST",
    body: formData,
  });

  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error("The server returned an invalid response.");
  }

  if (!response.ok || payload.success === false) {
    throw new Error(payload.error || "Receipt extraction failed.");
  }

  return payload;
}

export async function reextractDocument(documentType, extractionContext) {
  const response = await fetch(`${API_BASE_URL}/api/reextract`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      document_type: documentType,
      extraction_context: extractionContext,
    }),
  });

  const payload = await parseJson(response);

  if (!response.ok || payload.success === false) {
    throw new Error(payload.error || "Document re-extraction failed.");
  }

  return payload;
}

export async function fetchCostSummary() {
  const response = await fetch(`${API_BASE_URL}/api/cost-summary`);
  const payload = await parseJson(response);

  if (!response.ok || payload.success === false) {
    throw new Error(payload.error || "Failed to load cost summary.");
  }

  return payload.summary;
}

export async function fetchCostLog(limit = 50) {
  const response = await fetch(`${API_BASE_URL}/api/cost-log?limit=${encodeURIComponent(limit)}`);
  const payload = await parseJson(response);

  if (!response.ok || payload.success === false) {
    throw new Error(payload.error || "Failed to load cost log.");
  }

  return payload.records;
}

export async function resetCostLog() {
  const response = await fetch(`${API_BASE_URL}/api/cost-log`, {
    method: "DELETE",
  });
  const payload = await parseJson(response);

  if (!response.ok || payload.success === false) {
    throw new Error(payload.error || "Failed to reset cost log.");
  }

  return payload;
}

async function parseJson(response) {
  try {
    return await response.json();
  } catch {
    throw new Error("The server returned an invalid response.");
  }
}
