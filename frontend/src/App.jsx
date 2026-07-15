import { useEffect, useRef, useState } from "react";

import { extractReceipt, fetchCostSummary, reextractDocument, resetCostLog } from "./api.js";
import CostTracker from "./components/CostTracker.jsx";
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
  const [isReextracting, setIsReextracting] = useState(false);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [documentTypeHint, setDocumentTypeHint] = useState("auto");
  const [reextractType, setReextractType] = useState("receipt");
  const [costSummary, setCostSummary] = useState(null);
  const [costError, setCostError] = useState("");
  const [isCostLoading, setIsCostLoading] = useState(false);
  const timerRef = useRef(null);
  const startTimeRef = useRef(null);

  useEffect(() => {
    refreshCostSummary();

    return () => {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
      }
    };
  }, []);

  async function refreshCostSummary() {
    setIsCostLoading(true);
    setCostError("");

    try {
      const summary = await fetchCostSummary();
      setCostSummary(summary);
    } catch (err) {
      setCostError(err.message || "Failed to load cost summary.");
    } finally {
      setIsCostLoading(false);
    }
  }

  async function handleResetCostLog() {
    setIsCostLoading(true);
    setCostError("");

    try {
      await resetCostLog();
      await refreshCostSummary();
    } catch (err) {
      setCostError(err.message || "Failed to reset cost log.");
      setIsCostLoading(false);
    }
  }

  async function handleExtract() {
    if (!selectedFile) {
      setError("Choose a document image or PDF first.");
      return;
    }

    setIsLoading(true);
    setError("");
    setResult(null);
    startTimer();

    try {
      const response = await extractReceipt(selectedFile, documentTypeHint);
      setResult(response);
      setReextractType(response.data?.document_type === "unknown" ? "receipt" : response.data?.document_type || "receipt");
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      stopTimer();
      setIsLoading(false);
      refreshCostSummary();
    }
  }

  async function handleReextract() {
    if (!result?.data?.extraction_context) {
      setError("Re-extraction text is unavailable. Please scan the document again.");
      return;
    }

    setIsReextracting(true);
    setError("");
    startTimer();

    try {
      const response = await reextractDocument(reextractType, result.data.extraction_context);
      setResult((previous) => ({
        ...response,
        filename: previous?.filename || response.filename,
        data: {
          ...response.data,
          extraction_context: previous?.data?.extraction_context || response.data?.extraction_context,
        },
        image_preview: previous?.image_preview || null,
        pdf: previous?.pdf || response.pdf,
      }));
    } catch (err) {
      setError(err.message || "Document re-extraction failed.");
    } finally {
      stopTimer();
      setIsReextracting(false);
      refreshCostSummary();
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
            <h1>Document Extractor</h1>
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
            <div className="document-type-control">
              <label htmlFor="document-type-hint">Document Type</label>
              <select
                id="document-type-hint"
                value={documentTypeHint}
                onChange={(event) => setDocumentTypeHint(event.target.value)}
                disabled={isLoading || isReextracting}
              >
                <option value="auto">Auto</option>
                <option value="receipt">Receipt</option>
                <option value="invoice">Invoice</option>
                <option value="payment_receipt">Payment Receipt</option>
                <option value="delivery_order">Delivery Order</option>
              </select>
            </div>
            {(isLoading || isReextracting || elapsedMs > 0) && (
              <div className="processing-box">
                {isReextracting
                  ? `Re-extracting from scanned text... Elapsed time: ${formatSeconds(elapsedMs)}`
                  : isLoading
                  ? `Processing... Elapsed time: ${formatSeconds(elapsedMs)}`
                  : `Final elapsed time: ${formatSeconds(elapsedMs)}`}
              </div>
            )}
            {error && <div className="error-box">{error}</div>}
            <button className="primary-button" onClick={handleExtract} disabled={isLoading || isReextracting}>
              {isLoading ? "Extracting..." : "Extract Document"}
            </button>
          </section>

          <section className="results-column">
            <CostTracker
              summary={costSummary}
              error={costError}
              isLoading={isCostLoading}
              onRefresh={refreshCostSummary}
              onReset={handleResetCostLog}
            />
            {(selectedFile || result?.image_preview || isLoading) && (
              <ImagePreview
                selectedFile={selectedFile}
                imagePreview={result?.image_preview}
                isLoading={isLoading}
                pdfMetadata={result?.pdf}
              />
            )}
            {result ? (
              <>
                <ReextractControl
                  value={reextractType}
                  onChange={setReextractType}
                  onSubmit={handleReextract}
                  disabled={isLoading || isReextracting}
                  hasContext={Boolean(result.data?.extraction_context)}
                />
                <ResultViewer result={result} />
                <UsageCostPanel
                  usage={result.usage}
                  optimization={result.optimization}
                  backendProcessingTimeMs={result.processing_time_ms}
                  frontendElapsedMs={elapsedMs}
                />
                <OcrTextBox warnings={result.validation?.warnings || []} />
                <JsonViewer payload={result} />
              </>
            ) : !selectedFile && !isLoading ? (
              <div className="empty-state">
                <h2>Ready for a document</h2>
                <p>Upload a JPG, PNG, WEBP, or PDF document to extract structured fields.</p>
              </div>
            ) : null}
          </section>
        </div>
      </section>
    </main>
  );
}

function ReextractControl({ value, onChange, onSubmit, disabled, hasContext }) {
  return (
    <div className="panel reextract-panel">
      <div>
        <h2>Change Document Type</h2>
        <p>Re-extract from already scanned text without uploading or processing the image again.</p>
      </div>
      <div className="reextract-actions">
        <select value={value} onChange={(event) => onChange(event.target.value)} disabled={disabled}>
          <option value="receipt">Receipt</option>
          <option value="invoice">Invoice</option>
          <option value="payment_receipt">Payment Receipt</option>
          <option value="delivery_order">Delivery Order</option>
        </select>
        <button className="secondary-button" type="button" onClick={onSubmit} disabled={disabled || !hasContext}>
          Re-extract
        </button>
      </div>
      {!hasContext && <div className="usage-warning">Re-extraction text is unavailable. Please scan the document again.</div>}
    </div>
  );
}

function formatSeconds(milliseconds) {
  return `${(milliseconds / 1000).toFixed(1)}s`;
}

export default App;
