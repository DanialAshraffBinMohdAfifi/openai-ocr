import { useEffect, useState } from "react";

function ImagePreview({ selectedFile, imagePreview, isLoading }) {
  const [localPreviewUrl, setLocalPreviewUrl] = useState("");
  const metadata = imagePreview?.metadata || {};
  const originalImageUrl = imagePreview?.original_image_url || localPreviewUrl;
  const processedImageUrl = imagePreview?.processed_image_url;

  useEffect(() => {
    if (!selectedFile) {
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

      <div className="image-comparison-grid">
        <ImageCard
          title="Original Image"
          imageUrl={originalImageUrl}
          fallback="Choose a receipt image to preview it."
          meta={formatOriginalMeta(metadata)}
        />
        <ImageCard
          title="Processed Image"
          imageUrl={processedImageUrl}
          fallback={isLoading ? "Processing image..." : "Processed preview not available."}
          meta={formatProcessedMeta(metadata)}
        />
      </div>
    </div>
  );
}

function ImageCard({ title, imageUrl, fallback, meta }) {
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
    </article>
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
