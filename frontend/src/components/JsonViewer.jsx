function JsonViewer({ payload }) {
  const jsonText = JSON.stringify(payload, null, 2);

  async function copyJson() {
    await navigator.clipboard.writeText(jsonText);
  }

  function downloadJson() {
    const blob = new Blob([jsonText], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "receipt-extraction.json";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="panel">
      <div className="section-title">
        <h2>Raw JSON</h2>
        <div className="button-row">
          <button className="secondary-button compact" onClick={copyJson}>
            Copy JSON
          </button>
          <button className="secondary-button compact" onClick={downloadJson}>
            Download JSON
          </button>
        </div>
      </div>
      <pre className="json-viewer">{jsonText}</pre>
    </div>
  );
}

export default JsonViewer;
