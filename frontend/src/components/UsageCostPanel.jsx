function UsageCostPanel({ usage, optimization, backendProcessingTimeMs, frontendElapsedMs }) {
  const data = usage || {};
  const optimizationData = optimization || {};

  return (
    <div className="panel usage-panel">
      <div className="section-title">
        <h2>Token Usage & Estimated Cost</h2>
        <span>{formatMilliseconds(frontendElapsedMs)}</span>
      </div>

      {data.warning && <div className="usage-warning">{data.warning}</div>}

      <div className="usage-grid">
        <UsageMetric label="Model" value={data.model || "Not available"} />
        <UsageMetric label="Input Tokens" value={formatNumber(data.input_tokens)} />
        <UsageMetric label="Output Tokens" value={formatNumber(data.output_tokens)} />
        <UsageMetric label="Total Tokens" value={formatNumber(data.total_tokens)} />
        <UsageMetric label="Input Cost" value={formatUsd(data.input_cost_usd)} />
        <UsageMetric label="Output Cost" value={formatUsd(data.output_cost_usd)} />
        <UsageMetric label="Total Cost" value={formatUsd(data.total_cost_usd)} />
        <UsageMetric label="Estimated MYR" value={formatMyr(data.total_cost_myr)} />
        <UsageMetric label="Frontend Elapsed Time" value={formatMilliseconds(frontendElapsedMs)} />
        <UsageMetric label="Backend Processing Time" value={formatMilliseconds(backendProcessingTimeMs)} />
        <UsageMetric label="Prompt Mode" value={optimizationData.prompt_mode || "Not available"} />
        <UsageMetric label="Schema Mode" value={optimizationData.schema_mode || "Not available"} />
        <UsageMetric label="Detected Type" value={formatDocumentType(optimizationData.document_type)} />
        <UsageMetric label="Request Type" value={formatRequestType(optimizationData.request_type || data.request_type)} />
        <UsageMetric label="Image Input" value={formatBoolean(optimizationData.used_image_input ?? data.used_image_input)} />
        <UsageMetric label="Reused Text" value={formatBoolean(optimizationData.reused_extraction_context ?? data.reused_extraction_context)} />
        <UsageMetric label="Type Hint" value={formatDocumentType(optimizationData.document_type_hint || data.document_type_hint)} />
        <UsageMetric label="Image Max Dimension" value={formatPixels(optimizationData.image_max_dimension)} />
        <UsageMetric label="Images Sent" value={formatNumber(optimizationData.number_of_images_sent)} />
        <UsageMetric label="Prompt Length" value={formatCharacters(optimizationData.prompt_character_length)} />
      </div>
    </div>
  );
}

function UsageMetric({ label, value }) {
  return (
    <article className="usage-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function formatNumber(value) {
  if (typeof value !== "number") return "0";
  return new Intl.NumberFormat("en-US").format(value);
}

function formatUsd(value) {
  if (typeof value !== "number") return "$0.000000";
  return `$${value.toFixed(6)}`;
}

function formatMyr(value) {
  if (typeof value !== "number") return "RM 0.0000";
  return `RM ${value.toFixed(4)}`;
}

function formatMilliseconds(value) {
  if (typeof value !== "number") return "0 ms";
  return `${new Intl.NumberFormat("en-US").format(value)} ms`;
}

function formatPixels(value) {
  if (typeof value !== "number") return "Not available";
  return `${new Intl.NumberFormat("en-US").format(value)} px`;
}

function formatCharacters(value) {
  if (typeof value !== "number") return "0 chars";
  return `${new Intl.NumberFormat("en-US").format(value)} chars`;
}

function formatDocumentType(value) {
  if (!value) return "Not available";
  return String(value)
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function formatRequestType(value) {
  if (!value) return "Not available";
  return String(value)
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function formatBoolean(value) {
  if (typeof value !== "boolean") return "Not available";
  return value ? "Yes" : "No";
}

export default UsageCostPanel;
