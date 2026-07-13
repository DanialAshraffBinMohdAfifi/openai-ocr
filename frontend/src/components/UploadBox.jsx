import { useEffect, useRef, useState } from "react";

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];

function UploadBox({ selectedFile, isLoading, onFileSelect }) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [previewUrl, setPreviewUrl] = useState("");

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl("");
      return undefined;
    }

    const objectUrl = URL.createObjectURL(selectedFile);
    setPreviewUrl(objectUrl);

    return () => URL.revokeObjectURL(objectUrl);
  }, [selectedFile]);

  function chooseFile(file) {
    if (!file) return;
    if (!ACCEPTED_TYPES.includes(file.type)) {
      onFileSelect(null);
      return;
    }
    onFileSelect(file);
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
        accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
        disabled={isLoading}
        onChange={(event) => chooseFile(event.target.files?.[0])}
      />
      <div className="upload-icon">+</div>
      <h2>Drop receipt image here</h2>
      <p>JPG, JPEG, PNG, or WEBP up to the backend upload limit.</p>
      <button className="secondary-button" type="button" onClick={() => inputRef.current?.click()} disabled={isLoading}>
        Choose File
      </button>
      <div className="filename">{selectedFile ? selectedFile.name : "No file selected"}</div>
      {previewUrl && (
        <div className="receipt-preview">
          <img src={previewUrl} alt="Selected receipt preview" />
        </div>
      )}
    </div>
  );
}

export default UploadBox;
