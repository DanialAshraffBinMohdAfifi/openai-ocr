import { useEffect, useRef, useState } from "react";

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp", "application/pdf"];

function UploadBox({ selectedFile, isLoading, onFileSelect }) {
  const inputRef = useRef(null);
  const cameraInputRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [previewUrl, setPreviewUrl] = useState("");
  const [cameraMode, setCameraMode] = useState("idle");
  const [cameraError, setCameraError] = useState("");
  const [capturedPreviewUrl, setCapturedPreviewUrl] = useState("");

  useEffect(() => {
    if (!selectedFile || isPdfFile(selectedFile)) {
      setPreviewUrl("");
      return undefined;
    }

    const objectUrl = URL.createObjectURL(selectedFile);
    setPreviewUrl(objectUrl);

    return () => URL.revokeObjectURL(objectUrl);
  }, [selectedFile]);

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  useEffect(() => {
    if (videoRef.current && streamRef.current && cameraMode === "live") {
      videoRef.current.srcObject = streamRef.current;
    }
  }, [cameraMode]);

  function chooseFile(file) {
    if (!file) return;
    resetCameraState();
    if (!ACCEPTED_TYPES.includes(file.type)) {
      if (isPdfFile(file)) {
        onFileSelect(file);
        return;
      }
      onFileSelect(null);
      return;
    }
    onFileSelect(file);
  }

  async function startCamera() {
    setCameraError("");
    setCapturedPreviewUrl("");

    if (!window.isSecureContext) {
      setCameraError("Camera capture requires HTTPS or localhost.");
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError("Camera is not available on this device.");
      return;
    }

    try {
      stopCamera();
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      });
      streamRef.current = stream;
      setCameraMode("live");
    } catch (error) {
      setCameraMode("idle");
      setCameraError(cameraErrorMessage(error));
    }
  }

  function capturePhoto() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !video.videoWidth || !video.videoHeight) {
      setCameraError("Camera image is not ready yet. Please try again.");
      return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    setCapturedPreviewUrl(canvas.toDataURL("image/jpeg", 0.9));
    stopCamera();
    setCameraMode("captured");
  }

  async function retakePhoto() {
    setCapturedPreviewUrl("");
    await startCamera();
  }

  function useCapturedPhoto() {
    const canvas = canvasRef.current;
    if (!canvas) return;

    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setCameraError("Captured photo could not be prepared. Please try again.");
          return;
        }

        const file = new File([blob], `receipt-camera-capture-${timestampForFilename()}.jpg`, {
          type: "image/jpeg",
          lastModified: Date.now(),
        });
        resetCameraState();
        onFileSelect(file);
      },
      "image/jpeg",
      0.9
    );
  }

  function cancelCamera() {
    resetCameraState();
  }

  function resetCameraState() {
    stopCamera();
    setCameraMode("idle");
    setCameraError("");
    setCapturedPreviewUrl("");
  }

  function stopCamera() {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }

  return (
    <div
      className={`upload-box ${isDragging ? "dragging" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setIsDragging(false);
        chooseFile(event.dataTransfer.files?.[0]);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".jpg,.jpeg,.png,.webp,.pdf,image/jpeg,image/png,image/webp,application/pdf"
        disabled={isLoading}
        onChange={(event) => chooseFile(event.target.files?.[0])}
      />
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        disabled={isLoading}
        onChange={(event) => chooseFile(event.target.files?.[0])}
      />
      <div className="upload-icon">+</div>
      <h2>Upload Receipt or Document</h2>
      <p>JPG, JPEG, PNG, WEBP, or PDF up to the backend upload limit.</p>
      <div className="upload-actions">
        <button className="secondary-button" type="button" onClick={() => inputRef.current?.click()} disabled={isLoading}>
          Choose File
        </button>
        <button className="secondary-button" type="button" onClick={startCamera} disabled={isLoading || cameraMode === "live"}>
          Take Photo
        </button>
      </div>
      {cameraError && (
        <div className="camera-error">
          <span>{cameraError}</span>
          <button className="secondary-button compact" type="button" onClick={() => cameraInputRef.current?.click()} disabled={isLoading}>
            Use Camera Upload
          </button>
        </div>
      )}
      {cameraMode === "live" && (
        <div className="camera-panel">
          <strong>Camera Preview</strong>
          <video ref={videoRef} className="camera-video" autoPlay playsInline muted />
          <div className="camera-actions">
            <button className="primary-button camera-capture-button" type="button" onClick={capturePhoto} disabled={isLoading}>
              Capture
            </button>
            <button className="secondary-button" type="button" onClick={cancelCamera} disabled={isLoading}>
              Cancel
            </button>
          </div>
        </div>
      )}
      {cameraMode === "captured" && (
        <div className="camera-panel">
          <strong>Captured Photo</strong>
          <div className="receipt-preview camera-preview">
            <img src={capturedPreviewUrl} alt="Captured document preview" />
          </div>
          <div className="camera-actions">
            <button className="primary-button camera-use-button" type="button" onClick={useCapturedPhoto} disabled={isLoading}>
              Use Photo
            </button>
            <button className="secondary-button" type="button" onClick={retakePhoto} disabled={isLoading}>
              Retake
            </button>
            <button className="secondary-button" type="button" onClick={cancelCamera} disabled={isLoading}>
              Cancel
            </button>
          </div>
        </div>
      )}
      <canvas ref={canvasRef} className="camera-canvas" />
      <div className="filename">{selectedFile ? selectedFile.name : "No file selected"}</div>
      {previewUrl && (
        <div className="receipt-preview">
          <img src={previewUrl} alt="Selected document preview" />
        </div>
      )}
      {selectedFile && isPdfFile(selectedFile) && (
        <div className="pdf-file-card">
          <strong>PDF selected</strong>
          <span>Preview appears after extraction.</span>
        </div>
      )}
    </div>
  );
}

function isPdfFile(file) {
  return file.type === "application/pdf" || file.name?.toLowerCase().endsWith(".pdf");
}

function cameraErrorMessage(error) {
  if (error?.name === "NotAllowedError" || error?.name === "SecurityError") {
    return "Camera access was denied. Please allow camera permission or upload a file instead.";
  }
  if (error?.name === "NotFoundError" || error?.name === "OverconstrainedError") {
    return "Camera is not available on this device.";
  }
  if (!window.isSecureContext) {
    return "Camera capture requires HTTPS or localhost.";
  }
  return "Camera failed to start. Please upload a file instead.";
}

function timestampForFilename() {
  const now = new Date();
  const pad = (value) => String(value).padStart(2, "0");
  return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
}

export default UploadBox;
