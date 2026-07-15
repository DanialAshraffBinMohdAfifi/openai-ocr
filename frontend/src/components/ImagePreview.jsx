import { useEffect, useState } from "react";

function ImagePreview({ selectedFile, imagePreview, isLoading, pdfMetadata }) {
  const [localPreviewUrl, setLocalPreviewUrl] = useState("");
  const metadata = imagePreview?.metadata || {};
  const isPdfUpload = isPdfFile(selectedFile) || pdfMetadata?.is_pdf;
  const originalImageUrl = imagePreview?.original_image_url || localPreviewUrl;
  const processedImageUrl = imagePreview?.processed_image_url;

  useEffect(() => {
    if (!selectedFile || isPdfFile(selectedFile)) {
      setLocalPreviewUrl("");
      return undefined;
    }

    const objectUrl = URL.createObjectURL(selectedFile);
    setLocalPreviewUrl(objectUrl);

    return () => URL.revokeObjectURL(objectUrl);
  }, [selectedFile]);

  return (
    <div className="panel image-preview-panel">
      <div className="section-title">
        <h2>Image Preview</h2>
        {metadata.max_dimension && <span>Max {metadata.max_dimension}px</span>}
      </div>
      {pdfMetadata?.is_pdf && <PdfMetadata metadata={pdfMetadata} />}

      <div className="image-comparison-grid">
        <ImageCard
          title="Original Image"
          imageUrl={originalImageUrl}
          fallback={isPdfUpload ? "Rendered PDF preview appears after extraction." : "Choose a document image to preview it."}
          meta={formatOriginalMeta(metadata)}
        />
        <ImageCard
          title="Processed Image"
          imageUrl={processedImageUrl}
          fallback={isLoading ? "Processing image..." : "Processed preview not available."}
          meta={formatProcessedMeta(metadata)}
          details={<ProcessedDetails metadata={metadata} />}
        />
      </div>
    </div>
  );
}

function isPdfFile(file) {
  return file?.type === "application/pdf" || file?.name?.toLowerCase().endsWith(".pdf");
}

function PdfMetadata({ metadata }) {
  return (
    <div className="pdf-metadata-card">
      <strong>Source: PDF</strong>
      <span>Pages: {metadata.total_pdf_pages ?? "-"}</span>
      <span>Processed pages: {metadata.processed_pdf_pages ?? "-"}</span>
      <span>Render DPI: {metadata.pdf_render_dpi ?? "-"}</span>
      {metadata.pdf_warnings?.length > 0 && (
        <ul>
          {metadata.pdf_warnings.map((warning, index) => (
            <li key={`${warning}-${index}`}>{warning}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ImageCard({ title, imageUrl, fallback, meta, details }) {
  const [hasImageError, setHasImageError] = useState(false);
  const canShowImage = imageUrl && !hasImageError;

  useEffect(() => {
    setHasImageError(false);
  }, [imageUrl]);

  return (
    <article className="image-preview-card">
      <h3>{title}</h3>
      <div className="image-preview-frame">
        {canShowImage ? (
          <img className="image-preview-img" src={imageUrl} alt={`${title} preview`} onError={() => setHasImageError(true)} />
        ) : (
          <span>{imageUrl ? "Preview image could not be loaded." : fallback}</span>
        )}
      </div>
      {meta && <p className="image-preview-meta">{meta}</p>}
      {details}
    </article>
  );
}

function ProcessedDetails({ metadata }) {
  if (!metadata.processed_width || !metadata.processed_height) return null;

  const crop = metadata.crop || {};
  const cropApplied = crop.crop_applied ? "Yes" : "No";
  const confidence = typeof crop.crop_confidence === "number" ? `${Math.round(crop.crop_confidence * 100)}%` : null;
  const paddingRatio = typeof crop.crop_padding_ratio === "number" ? `${Math.round(crop.crop_padding_ratio * 100)}%` : null;

  return (
    <div className="image-preview-details">
      <strong>Optimized automatically</strong>
      <span>Mode: {metadata.selected_preprocessing_mode || "auto"}</span>
      <span>Crop Applied: {cropApplied}</span>
      <span>Crop Method: {crop.crop_method || "none"}</span>
      {confidence && <span>Crop Confidence: {confidence}</span>}
      <span>Perspective Correction: {crop.perspective_corrected ? "Yes" : "No"}</span>
      {paddingRatio && <span>Padding Ratio: {paddingRatio}</span>}
      {!crop.crop_applied && crop.crop_reason && <span>Reason: {crop.crop_reason}</span>}
      <span>
        Size: {metadata.processed_width} x {metadata.processed_height}
      </span>
      <span>
        Format: {metadata.processed_format || "JPEG"} Quality {metadata.jpeg_quality || "-"}
      </span>
      {metadata.candidate_scores && <DebugScores scores={metadata.candidate_scores} />}
      {metadata.pdf?.is_pdf && <span>Source: PDF page render</span>}
    </div>
  );
}

function DebugScores({ scores }) {
  return (
    <details className="image-preview-debug">
      <summary>Candidate scores</summary>
      <ul>
        {Object.entries(scores).map(([name, score]) => (
          <li key={name}>
            {name}: {Number(score).toFixed(2)}
          </li>
        ))}
      </ul>
    </details>
  );
}

function formatOriginalMeta(metadata) {
  if (!metadata.original_width || !metadata.original_height) return "";
  return `${metadata.original_width} x ${metadata.original_height}`;
}

function formatProcessedMeta(metadata) {
  if (!metadata.processed_width || !metadata.processed_height) return "";

  const parts = [
    `${metadata.processed_width} x ${metadata.processed_height}`,
    metadata.processed_format,
    metadata.jpeg_quality ? `Quality ${metadata.jpeg_quality}` : "",
  ].filter(Boolean);

  return parts.join(" - ");
}

export default ImagePreview;
