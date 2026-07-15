function CostTracker({ summary, error, isLoading, onRefresh, onReset }) {
  const data = summary || {};
  const showReset = import.meta.env.DEV;

  return (
    <div className="panel usage-panel">
      <div className="section-title">
        <h2>Testing Cost Tracker</h2>
        <div className="cost-actions">
          <button type="button" className="secondary-button" onClick={onRefresh} disabled={isLoading}>
            {isLoading ? "Refreshing..." : "Refresh Cost Summary"}
          </button>
          {showReset && (
            <button type="button" className="secondary-button danger-button" onClick={onReset} disabled={isLoading}>
              Reset Cost Log
            </button>
          )}
        </div>
      </div>

      {error && <div className="usage-warning">{error}</div>}

      <div className="usage-grid">
        <CostMetric label="Total Requests" value={formatNumber(data.total_requests)} />
        <CostMetric label="Successful Requests" value={formatNumber(data.successful_requests)} />
        <CostMetric label="Failed Requests" value={formatNumber(data.failed_requests)} />
        <CostMetric label="Input Tokens" value={formatNumber(data.total_input_tokens)} />
        <CostMetric label="Output Tokens" value={formatNumber(data.total_output_tokens)} />
        <CostMetric label="Total Tokens" value={formatNumber(data.total_tokens)} />
        <CostMetric label="Total Cost USD" value={formatUsd(data.total_cost_usd)} />
        <CostMetric label="Total Cost MYR" value={formatMyr(data.total_cost_myr)} />
        <CostMetric label="Average per Extraction" value={`${formatUsd(data.average_cost_usd)} / ${formatMyr(data.average_cost_myr)}`} />
      </div>
    </div>
  );
}

function CostMetric({ label, value }) {
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

export default CostTracker;
