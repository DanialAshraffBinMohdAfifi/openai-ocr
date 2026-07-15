function ResultViewer({ result }) {
  const payload = result.data || {};
  const documentType = payload.document_type || "unknown";
  const data = payload.data || {};
  const common = payload.common || {};

  return (
    <div className="panel">
      <div className="section-title">
        <h2>Extraction Result</h2>
        <span>{result.processing_time_ms} ms</span>
      </div>

      <div className="document-type-banner">
        <span>Detected Document Type</span>
        <strong>{formatDocumentType(documentType)}</strong>
      </div>

      {documentType === "receipt" && <ReceiptView data={data} />}
      {documentType === "invoice" && <InvoiceView data={data} />}
      {documentType === "payment_receipt" && <PaymentReceiptView data={data} />}
      {documentType === "delivery_order" && <DeliveryOrderView data={data} />}
      {documentType === "unknown" && <UnknownView data={data} common={common} />}
    </div>
  );
}

function ReceiptView({ data }) {
  return (
    <>
      <CardSection
        title="Document Info"
        cards={[
          ["Receipt Date", data.receipt_date],
          ["Receipt Number", data.receipt_number],
          ["Category", data.category],
        ]}
      />
      <CardSection title="Vendor Info" cards={[["Vendor Name", data.vendor_name]]} />
      <CardSection
        title="Payment Info"
        cards={[
          ["Payment Method", data.payment_method],
          ["Currency", data.currency],
        ]}
      />
      <CardSection
        title="Amount Breakdown"
        cards={[
          ["Subtotal", formatMoney(data.subtotal, data.currency)],
          ["Tax / SST", formatMoney(data.tax_sst_amount, data.currency)],
          ["Total Amount", formatMoney(data.total_amount, data.currency)],
        ]}
      />
      <ItemsTable
        items={data.items}
        columns={[
          ["Item Name", (item) => displayValue(item.name || "Unknown item")],
          ["Quantity", (item) => displayValue(item.quantity)],
          ["Unit Price", (item) => formatOptionalMoney(item.unit_price, data.currency)],
          ["Line Total", (item) => formatMoney(item.line_total, data.currency)],
        ]}
      />
    </>
  );
}

function InvoiceView({ data }) {
  return (
    <>
      <CardSection
        title="Document Info"
        cards={[
          ["Invoice Number", data.invoice_number],
          ["Invoice Date", data.invoice_date],
          ["Due Date", data.due_date],
        ]}
      />
      <CardSection
        title="Vendor / Customer Info"
        cards={[
          ["Vendor Name", data.vendor_name],
          ["Customer Name", data.customer_name],
        ]}
      />
      <CardSection
        title="Amount Breakdown"
        cards={[
          ["Subtotal", formatMoney(data.subtotal, data.currency)],
          ["Tax / SST", formatMoney(data.tax_sst_amount, data.currency)],
          ["Total Amount", formatMoney(data.total_amount, data.currency)],
          ["Currency", data.currency],
        ]}
      />
      <ItemsTable
        items={data.items}
        columns={[
          ["Item Name", (item) => displayValue(item.name || "Unknown item")],
          ["Quantity", (item) => displayValue(item.quantity)],
          ["Unit", (item) => displayValue(item.unit)],
          ["Unit Price", (item) => formatOptionalMoney(item.unit_price, data.currency)],
          ["Line Total", (item) => formatMoney(item.line_total, data.currency)],
        ]}
      />
    </>
  );
}

function PaymentReceiptView({ data }) {
  return (
    <>
      <CardSection title="Document Info" cards={[["Receipt Number", data.receipt_number], ["Payment Date", data.payment_date], ["Reference Number", data.reference_number]]} />
      <CardSection title="Party Info" cards={[["Vendor Name", data.vendor_name], ["Payer Name", data.payer_name]]} />
      <CardSection
        title="Payment Info"
        cards={[
          ["Payment Method", data.payment_method],
          ["Total Amount Received", formatMoney(data.total_amount_received, data.currency)],
          ["Currency", data.currency],
        ]}
      />
      <ItemsTable
        items={data.items}
        columns={[
          ["Invoice Number", (item) => displayValue(item.invoice_number)],
          ["Description", (item) => displayValue(item.description)],
          ["Line Total", (item) => formatMoney(item.line_total, data.currency)],
        ]}
      />
    </>
  );
}

function DeliveryOrderView({ data }) {
  return (
    <>
      <CardSection
        title="Document Info"
        cards={[
          ["Delivery Order Number", data.delivery_order_number],
          ["Delivery Date", data.delivery_date],
          ["Customer PO Number", data.customer_po_number],
        ]}
      />
      <CardSection
        title="Party / Delivery Info"
        cards={[
          ["Vendor Name", data.vendor_name],
          ["Customer Name", data.customer_name],
          ["Deliver To", data.deliver_to],
        ]}
      />
      <ItemsTable
        items={data.items}
        columns={[
          ["Item Code", (item) => displayValue(item.item_code)],
          ["Description", (item) => displayValue(item.description || "Unknown item")],
          ["Quantity", (item) => displayValue(item.quantity)],
          ["Unit", (item) => displayValue(item.unit)],
          ["Remarks", (item) => displayValue(item.remarks)],
        ]}
      />
    </>
  );
}

function UnknownView({ data, common }) {
  const currency = common.currency;

  return (
    <>
      <div className="warning-box">The system could not confidently identify this document. Please review manually.</div>
      <CardSection
        title="Common Details"
        cards={[
          ["Source Name", common.source_name],
          ["Recipient Name", common.recipient_name],
          ["Document Date", common.document_date],
          ["Document Number", common.document_number],
          ["Reference Number", common.reference_number],
          ["Currency", common.currency],
        ]}
      />
      <CardSection
        title="Possible Document Info"
        cards={[
          ["Visible Title", data.visible_title],
          ["Summary", data.summary, true],
        ]}
      />
      <ItemsTable
        title="Key Values"
        items={data.key_values}
        emptyLabel="No key-value fields detected."
        columns={[
          ["Label", (item) => displayValue(item.label)],
          ["Value", (item) => displayValue(item.value)],
        ]}
      />
      <ItemsTable
        title="Possible Items / Rows"
        items={data.items}
        emptyLabel="No item rows detected."
        columns={[
          ["Description", (item) => displayValue(item.description)],
          ["Quantity", (item) => displayValue(item.quantity)],
          ["Unit", (item) => displayValue(item.unit)],
          ["Unit Price", (item) => formatOptionalMoney(item.unit_price, currency)],
          ["Line Total", (item) => formatOptionalMoney(item.line_total, currency)],
          ["Remarks", (item) => displayValue(item.remarks)],
        ]}
      />
    </>
  );
}

function CardSection({ title, cards }) {
  return (
    <section className="result-section">
      <h3>{title}</h3>
      <div className="summary-grid">
        {cards.map(([label, value, wide]) => (
          <SummaryCard key={label} label={label} value={displayValue(value)} wide={wide} />
        ))}
      </div>
    </section>
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

function ItemsTable({ items, columns, title = "Items", emptyLabel = "No items extracted." }) {
  return (
    <section className="result-section">
      <h3>{title}</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {columns.map(([label]) => (
                <th key={label}>{label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.isArray(items) && items.length ? (
              items.map((item, index) => (
                <tr key={index}>
                  {columns.map(([label, render]) => (
                    <td key={label}>{render(item)}</td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columns.length} className="empty-row">
                  {emptyLabel}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function formatMoney(value, currency) {
  if (typeof value !== "number") return "-";
  const prefix = currency ? `${formatCurrencyPrefix(currency)} ` : "";
  return `${prefix}${value.toFixed(2)}`;
}

function formatOptionalMoney(value, currency) {
  if (typeof value !== "number") return "-";
  return formatMoney(value, currency);
}

function formatCurrencyPrefix(currency) {
  return currency === "MYR" ? "RM" : currency;
}

function displayValue(value) {
  return value === null || value === undefined || value === "" ? "-" : value;
}

function formatDocumentType(documentType) {
  return String(documentType || "unknown")
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export default ResultViewer;
