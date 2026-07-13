function UsageCostPanel({ usage, backendProcessingTimeMs, frontendElapsedMs }) {
  const data = usage || {};

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
  if (typeof value !== "number") return "RM0.0000";
  return `RM${value.toFixed(4)}`;
}

function formatMilliseconds(value) {
  if (typeof value !== "number") return "0 ms";
  return `${new Intl.NumberFormat("en-US").format(value)} ms`;
}

export default UsageCostPanel;
