RECEIPT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "vendor_name": {"type": ["string", "null"]},
        "receipt_date": {"type": ["string", "null"]},
        "receipt_number": {"type": ["string", "null"]},
        "reference_number": {"type": ["string", "null"]},
        "total_amount": {"type": ["number", "null"]},
        "tax_sst_amount": {"type": ["number", "null"]},
        "short_description": {"type": ["string", "null"]},
        "currency": {"type": ["string", "null"]},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": ["string", "null"]},
                    "quantity": {"type": ["number", "null"]},
                    "amount": {"type": ["number", "null"]},
                    "total": {"type": ["number", "null"]},
                },
                "required": ["name", "quantity", "amount", "total"],
            },
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "vendor_name",
        "receipt_date",
        "receipt_number",
        "reference_number",
        "total_amount",
        "tax_sst_amount",
        "short_description",
        "currency",
        "items",
        "warnings",
    ],
}

RECEIPT_PROMPT = """
Extract receipt data from the uploaded receipt image.

The image is the source of truth. Do not guess hidden, cropped, or unreadable text.
Use null for missing fields. Money values must be numbers, not strings.
Normalize receipt_date to YYYY-MM-DD when possible.
Detect currency from the receipt, such as MYR for RM/MYR, and use null if not visible or inferable.
Preserve item names exactly as written on the receipt.
Include warnings for unreadable fields, uncertain values, missing important fields, or math mismatches.
Return strict valid JSON only. Do not include markdown. Do not include any explanation.
Do not include extra fields.

Return exactly this JSON structure:
{
  "vendor_name": null,
  "receipt_date": null,
  "receipt_number": null,
  "reference_number": null,
  "total_amount": null,
  "tax_sst_amount": null,
  "short_description": null,
  "currency": null,
  "items": [
    {
      "name": null,
      "quantity": null,
      "amount": null,
      "total": null
    }
  ],
  "warnings": []
}
""".strip()
