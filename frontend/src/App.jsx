import { useEffect, useRef, useState } from "react";

import { extractReceipt } from "./api.js";
import ImagePreview from "./components/ImagePreview.jsx";
import JsonViewer from "./components/JsonViewer.jsx";
import OcrTextBox from "./components/OcrTextBox.jsx";
import ResultViewer from "./components/ResultViewer.jsx";
import UploadBox from "./components/UploadBox.jsx";
import UsageCostPanel from "./components/UsageCostPanel.jsx";

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [elapsedMs, setElapsedMs] = useState(0);
  const timerRef = useRef(null);
  const startTimeRef = useRef(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
      }
    };
  }, []);

  async function handleExtract() {
    if (!selectedFile) {
      setError("Choose a receipt image first.");
      return;
    }

    setIsLoading(true);
    setError("");
    setResult(null);
    startTimer();

    try {
      const response = await extractReceipt(selectedFile);
      setResult(response);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      stopTimer();
      setIsLoading(false);
    }
  }

  function startTimer() {
    stopTimer();
    setElapsedMs(0);
    startTimeRef.current = Date.now();
    timerRef.current = window.setInterval(() => {
      setElapsedMs(Date.now() - startTimeRef.current);
    }, 100);
  }

  function stopTimer() {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (startTimeRef.current) {
      setElapsedMs(Date.now() - startTimeRef.current);
      startTimeRef.current = null;
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <header className="app-header">
          <div>
            <p className="eyebrow">Phase 1</p>
            <h1>Receipt Extractor</h1>
          </div>
          <span className="status-pill">Image to JSON</span>
        </header>

        <div className="layout-grid">
          <section className="panel upload-panel">
            <UploadBox
              selectedFile={selectedFile}
              isLoading={isLoading}
              onFileSelect={(file) => {
                setSelectedFile(file);
                setError("");
                setElapsedMs(0);
              }}
            />
            {(isLoading || elapsedMs > 0) && (
              <div className="processing-box">
                {isLoading
                  ? `Processing... Elapsed time: ${formatSeconds(elapsedMs)}`
                  : `Final elapsed time: ${formatSeconds(elapsedMs)}`}
              </div>
            )}
            {error && <div className="error-box">{error}</div>}
            <button className="primary-button" onClick={handleExtract} disabled={isLoading}>
              {isLoading ? "Extracting..." : "Extract Receipt"}
            </button>
          </section>

          <section className="results-column">
            {(selectedFile || result?.image_preview || isLoading) && (
              <ImagePreview selectedFile={selectedFile} imagePreview={result?.image_preview} isLoading={isLoading} />
            )}
            {result ? (
              <>
                <ResultViewer result={result} />
                <UsageCostPanel
                  usage={result.usage}
                  backendProcessingTimeMs={result.processing_time_ms}
                  frontendElapsedMs={elapsedMs}
                />
                <OcrTextBox warnings={result.validation?.warnings || []} />
                <JsonViewer payload={result} />
              </>
            ) : !selectedFile && !isLoading ? (
              <div className="empty-state">
                <h2>Ready for a receipt</h2>
                <p>Upload a JPG, PNG, or WEBP receipt image to extract structured fields.</p>
              </div>
            ) : null}
          </section>
        </div>
      </section>
    </main>
  );
}

function formatSeconds(milliseconds) {
  return `${(milliseconds / 1000).toFixed(1)}s`;
}

export default App;
