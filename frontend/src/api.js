const API_BASE_URL = "http://localhost:5000";

export async function extractReceipt(file) {
  const formData = new FormData();
  formData.append("file", file);

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
