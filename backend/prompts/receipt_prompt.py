DOCUMENT_TYPES = ["receipt", "invoice", "payment_receipt", "delivery_order", "unknown"]
DOCUMENT_TYPE_HINTS = ["auto", "receipt", "invoice", "payment_receipt", "delivery_order"]


def _object_schema(properties):
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(properties.keys()),
    }


def _array_schema(item_properties):
    return {
        "type": "array",
        "items": _object_schema(item_properties),
    }


MONEY = {"type": ["number", "null"]}
TEXT = {"type": ["string", "null"]}
NUMBER = {"type": ["number", "null"]}


RECEIPT_DATA_SCHEMA = _object_schema(
    {
        "vendor_name": TEXT,
        "receipt_date": TEXT,
        "receipt_number": TEXT,
        "payment_method": TEXT,
        "subtotal": MONEY,
        "tax_sst_amount": MONEY,
        "total_amount": MONEY,
        "currency": TEXT,
        "category": TEXT,
        "items": _array_schema(
            {
                "name": TEXT,
                "quantity": NUMBER,
                "unit_price": MONEY,
                "line_total": MONEY,
            }
        ),
    }
)

INVOICE_DATA_SCHEMA = _object_schema(
    {
        "vendor_name": TEXT,
        "customer_name": TEXT,
        "invoice_number": TEXT,
        "invoice_date": TEXT,
        "due_date": TEXT,
        "subtotal": MONEY,
        "tax_sst_amount": MONEY,
        "total_amount": MONEY,
        "currency": TEXT,
        "items": _array_schema(
            {
                "name": TEXT,
                "quantity": NUMBER,
                "unit": TEXT,
                "unit_price": MONEY,
                "line_total": MONEY,
            }
        ),
    }
)

PAYMENT_RECEIPT_DATA_SCHEMA = _object_schema(
    {
        "vendor_name": TEXT,
        "payer_name": TEXT,
        "receipt_number": TEXT,
        "payment_date": TEXT,
        "reference_number": TEXT,
        "payment_method": TEXT,
        "total_amount_received": MONEY,
        "currency": TEXT,
        "items": _array_schema(
            {
                "invoice_number": TEXT,
                "description": TEXT,
                "line_total": MONEY,
            }
        ),
    }
)

DELIVERY_ORDER_DATA_SCHEMA = _object_schema(
    {
        "vendor_name": TEXT,
        "delivery_order_number": TEXT,
        "delivery_date": TEXT,
        "customer_name": TEXT,
        "customer_po_number": TEXT,
        "deliver_to": TEXT,
        "items": _array_schema(
            {
                "item_code": TEXT,
                "description": TEXT,
                "quantity": NUMBER,
                "unit": TEXT,
                "remarks": TEXT,
            }
        ),
    }
)

UNKNOWN_COMMON_SCHEMA = _object_schema(
    {
        "source_name": TEXT,
        "recipient_name": TEXT,
        "document_date": TEXT,
        "document_number": TEXT,
        "reference_number": TEXT,
        "currency": TEXT,
    }
)

UNKNOWN_DATA_SCHEMA = _object_schema(
    {
        "visible_title": TEXT,
        "summary": TEXT,
        "key_values": _array_schema(
            {
                "label": TEXT,
                "value": TEXT,
            }
        ),
        "items": _array_schema(
            {
                "description": TEXT,
                "quantity": NUMBER,
                "unit": TEXT,
                "unit_price": MONEY,
                "line_total": MONEY,
                "remarks": TEXT,
            }
        ),
    }
)

RECEIPT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "document_type": {"type": "string", "enum": DOCUMENT_TYPES},
        "common": {
            "anyOf": [
                UNKNOWN_COMMON_SCHEMA,
                {"type": "null"},
            ]
        },
        "data": {
            "anyOf": [
                RECEIPT_DATA_SCHEMA,
                INVOICE_DATA_SCHEMA,
                PAYMENT_RECEIPT_DATA_SCHEMA,
                DELIVERY_ORDER_DATA_SCHEMA,
                UNKNOWN_DATA_SCHEMA,
            ]
        },
        "extraction_context": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "raw_text": TEXT,
                "key_value_text": TEXT,
                "tables_text": TEXT,
            },
            "required": ["raw_text", "key_value_text", "tables_text"],
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["document_type", "common", "data", "extraction_context", "warnings"],
}

DATA_SCHEMAS = {
    "receipt": RECEIPT_DATA_SCHEMA,
    "invoice": INVOICE_DATA_SCHEMA,
    "payment_receipt": PAYMENT_RECEIPT_DATA_SCHEMA,
    "delivery_order": DELIVERY_ORDER_DATA_SCHEMA,
    "unknown": UNKNOWN_DATA_SCHEMA,
}

REEXTRACT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "document_type": {"type": "string", "enum": DOCUMENT_TYPES},
        "common": {
            "anyOf": [
                UNKNOWN_COMMON_SCHEMA,
                {"type": "null"},
            ]
        },
        "data": {
            "anyOf": [
                RECEIPT_DATA_SCHEMA,
                INVOICE_DATA_SCHEMA,
                PAYMENT_RECEIPT_DATA_SCHEMA,
                DELIVERY_ORDER_DATA_SCHEMA,
                UNKNOWN_DATA_SCHEMA,
            ]
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["document_type", "common", "data", "warnings"],
}

RECEIPT_PROMPT = """
Extract important accounting fields from the uploaded document image/PDF page.
Classify document_type, then fill only the matching simplified schema in data.
Return strict valid JSON only. No markdown. No explanation.

Top-level response:
{
  "document_type": "receipt|invoice|payment_receipt|delivery_order|unknown",
  "common": null,
  "data": {},
  "warnings": []
}

Document types:
- receipt: POS, restaurant, grocery, petrol, retail receipt.
- invoice: supplier invoice, tax invoice, company invoice, bill requesting payment.
- payment_receipt: official receipt, payment acknowledgement, proof of payment, paid invoice list.
- delivery_order: delivery order, goods delivery note, inventory delivery document.
- unknown: unclear document type.

Simplified schemas:
- receipt: vendor_name, receipt_date, receipt_number, payment_method, subtotal, tax_sst_amount, total_amount, currency, category, items[{name, quantity, unit_price, line_total}]
- invoice: vendor_name, customer_name, invoice_number, invoice_date, due_date, subtotal, tax_sst_amount, total_amount, currency, items[{name, quantity, unit, unit_price, line_total}]
- payment_receipt: vendor_name, payer_name, receipt_number, payment_date, reference_number, payment_method, total_amount_received, currency, items[{invoice_number, description, line_total}]
- delivery_order: vendor_name, delivery_order_number, delivery_date, customer_name, customer_po_number, deliver_to, items[{item_code, description, quantity, unit, remarks}]
- unknown: common{source_name, recipient_name, document_date, document_number, reference_number, currency}, data{visible_title, summary, key_values[{label, value}], items[{description, quantity, unit, unit_price, line_total, remarks}]}

Rules:
- Use null for missing visible fields. Do not hallucinate.
- Money values must be numbers, not strings.
- If RM is visible, currency = "MYR".
- Normalize dates to YYYY-MM-DD when possible.
- For known document types, set common to null and fill only the matching known data schema.
- Use document_type = "unknown" only when the document type is unclear or confidence is low.
- For unknown documents, do not force the document into receipt, invoice, payment_receipt, or delivery_order.
- For unknown documents, fill common with shared visible facts: source_name, recipient_name, document_date, document_number, reference_number, currency.
- For unknown documents, key_values should contain useful visible label-value pairs that do not fit common.
- For unknown documents, items should contain possible table rows, goods, services, listed entries, or line items.
- For unknown documents, if a table row is visible but column meanings are unclear, put readable row text in description and use null for unclear fields.
- For unknown documents, warnings must include "Document type is unknown. Please review manually."
- unit_price means price per unit only.
- line_total means row total.
- If only Amount, Amount (RM), Total, or Line Total exists, put the value in line_total and set unit_price to null.
- Do not calculate unit_price unless explicitly visible.
- Keep warnings for uncertain, unreadable, or conflicting fields.
""".strip()

RECEIPT_PROMPT_NORMAL = RECEIPT_PROMPT

RECEIPT_PROMPT_COMPACT = RECEIPT_PROMPT


def get_receipt_prompt(mode=None):
    selected_mode = (mode or "compact").strip().lower()
    if selected_mode == "normal":
        return RECEIPT_PROMPT_NORMAL, "normal"
    return RECEIPT_PROMPT_COMPACT, "compact"


def get_document_extraction_prompt(document_type_hint="auto", mode=None):
    selected_hint = normalize_document_type_hint(document_type_hint)
    base_prompt, prompt_mode = get_receipt_prompt(mode)

    if selected_hint == "auto":
        hint_prompt = "Document type hint: auto. Classify the document type from the image."
    else:
        hint_prompt = (
            f"Document type hint: {selected_hint}. Use only the {selected_hint} schema. "
            "Set document_type to this value unless the document is clearly incompatible; if incompatible, keep the selected schema and add a warning."
        )

    context_prompt = (
        "Also return extraction_context with concise reusable scanned text: "
        "raw_text, key_value_text, and tables_text. Do not include base64 or image metadata."
    )
    return f"{base_prompt}\n\n{hint_prompt}\n{context_prompt}", prompt_mode


def get_text_reextract_prompt(document_type, extraction_context, mode=None):
    selected_type = normalize_specific_document_type(document_type)
    _base_prompt, prompt_mode = get_receipt_prompt(mode)
    context = _format_context(extraction_context)
    prompt = f"""
Re-extract structured data from already scanned text only.
Do not ask for or assume image input.
Use only the {selected_type} schema and return valid JSON only.

Top-level response:
{{
  "document_type": "{selected_type}",
  "data": {{}},
  "warnings": []
}}

Rules:
- Use null for missing visible fields.
- Money values must be numbers, not strings.
- If RM is visible, currency = "MYR".
- Normalize dates to YYYY-MM-DD when possible.
- unit_price means price per unit only.
- line_total means row total.
- If only Amount/Total/Line Total exists, put it in line_total and set unit_price to null.

Scanned text context:
{context}
""".strip()
    return prompt, prompt_mode


def build_response_schema(document_type_hint="auto", include_extraction_context=True):
    selected_hint = normalize_document_type_hint(document_type_hint)
    schema = RECEIPT_SCHEMA if include_extraction_context else REEXTRACT_SCHEMA

    if selected_hint == "auto":
        return schema

    data_schema = DATA_SCHEMAS[selected_hint]
    properties = {
        "document_type": {"type": "string", "enum": [selected_hint]},
        "data": data_schema,
        "warnings": {"type": "array", "items": {"type": "string"}},
    }
    required = ["document_type", "data", "warnings"]

    if include_extraction_context:
        properties["extraction_context"] = RECEIPT_SCHEMA["properties"]["extraction_context"]
        required.insert(2, "extraction_context")

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required,
    }


def normalize_document_type_hint(value):
    normalized = str(value or "auto").strip().lower()
    return normalized if normalized in DOCUMENT_TYPE_HINTS else "auto"


def normalize_specific_document_type(value):
    normalized = str(value or "").strip().lower()
    return normalized if normalized in DOCUMENT_TYPES and normalized != "unknown" else "receipt"


def _format_context(extraction_context):
    context = extraction_context if isinstance(extraction_context, dict) else {}
    raw_text = context.get("raw_text") or ""
    key_value_text = context.get("key_value_text") or ""
    tables_text = context.get("tables_text") or ""
    return (
        f"raw_text:\n{raw_text}\n\n"
        f"key_value_text:\n{key_value_text}\n\n"
        f"tables_text:\n{tables_text}"
    )
