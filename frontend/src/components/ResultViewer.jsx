function ResultViewer({ result }) {
  const data = result.data || {};
  const receiptId = data.receipt_number || data.reference_number || "Not found";

  return (
    <div className="panel">
      <div className="section-title">
        <h2>Extraction Result</h2>
        <span>{result.processing_time_ms} ms</span>
      </div>

      <div className="summary-grid">
        <SummaryCard label="Vendor" value={data.vendor_name || "Not found"} />
        <SummaryCard label="Receipt Date" value={data.receipt_date || "Not found"} />
        <SummaryCard label="Receipt / Reference" value={receiptId} />
        <SummaryCard label="Total Amount" value={formatMoney(data.total_amount, data.currency)} />
        <SummaryCard label="Tax / SST" value={formatMoney(data.tax_sst_amount, data.currency)} />
        <SummaryCard label="Description" value={data.short_description || "Not available"} wide />
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Item name</th>
              <th>Quantity</th>
              <th>Amount</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            {(data.items || []).length ? (
              data.items.map((item, index) => (
                <tr key={`${item.name}-${index}`}>
                  <td>{item.name || "Unknown item"}</td>
                  <td>{formatValue(item.quantity)}</td>
                  <td>{formatMoney(item.amount, data.currency)}</td>
                  <td>{formatMoney(item.total, data.currency)}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="4" className="empty-row">
                  No items extracted.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SummaryCard({ label, value, wide = false }) {
  return (
    <article className={`summary-card ${wide ? "wide" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function formatMoney(value, currency) {
  if (typeof value !== "number") return "Not found";
  const prefix = currency ? `${currency} ` : "";
  return `${prefix}${value.toFixed(2)}`;
}

function formatValue(value) {
  return value === null || value === undefined ? "Not found" : value;
}

export default ResultViewer;
