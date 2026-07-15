import json
import os

from openai import OpenAI, OpenAIError

from prompts.receipt_prompt import (
    DOCUMENT_TYPES,
    build_response_schema,
    get_document_extraction_prompt,
    get_text_reextract_prompt,
    normalize_document_type_hint,
    normalize_specific_document_type,
)
from services.cost_service import calculate_openai_cost, safe_get_token_usage


class OpenAIExtractionError(Exception):
    pass


def extract_receipt_data(image_data_url, image_metadata=None, document_type_hint="auto"):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise OpenAIExtractionError(
            "OpenAI API key is not configured. Please create backend/.env based on "
            "backend/.env.example and set OPENAI_API_KEY."
        )

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    normalized_hint = normalize_document_type_hint(document_type_hint)
    prompt, prompt_mode = get_document_extraction_prompt(normalized_hint, os.getenv("OPENAI_PROMPT_MODE", "compact"))
    response_schema = build_response_schema(normalized_hint, include_extraction_context=True)
    image_data_urls = image_data_url if isinstance(image_data_url, list) else [image_data_url]
    optimization = _build_optimization_metadata(prompt, prompt_mode, image_data_urls, image_metadata)
    optimization["request_type"] = "image_extraction"
    optimization["used_image_input"] = True
    optimization["document_type_hint"] = normalized_hint
    optimization["reused_extraction_context"] = False
    _log_safe_request_debug(model, optimization, image_metadata)

    try:
        content = [{"type": "input_text", "text": prompt}]
        content.extend({"type": "input_image", "image_url": image_url} for image_url in image_data_urls)

        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "document_extraction",
                    "schema": response_schema,
                    "strict": True,
                }
            },
        )
    except OpenAIError as exc:
        raise OpenAIExtractionError("OpenAI extraction request failed.") from exc

    raw_text = getattr(response, "output_text", None)
    if not raw_text:
        raise OpenAIExtractionError("OpenAI returned an empty response.")

    token_usage = safe_get_token_usage(response)
    cost_data = calculate_openai_cost(token_usage, model)

    extracted_data = _normalize_document_data(_parse_json(raw_text))
    optimization["schema_mode"] = "simplified_document_specific"
    optimization["document_type"] = extracted_data["document_type"]
    _attach_request_metadata(cost_data, optimization)

    return extracted_data, cost_data, optimization


def reextract_receipt_data(document_type, extraction_context):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise OpenAIExtractionError(
            "OpenAI API key is not configured. Please create backend/.env based on "
            "backend/.env.example and set OPENAI_API_KEY."
        )

    selected_type = normalize_specific_document_type(document_type)
    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    prompt, prompt_mode = get_text_reextract_prompt(selected_type, extraction_context, os.getenv("OPENAI_PROMPT_MODE", "compact"))
    response_schema = build_response_schema(selected_type, include_extraction_context=False)
    optimization = {
        "prompt_mode": prompt_mode,
        "prompt_character_length": len(prompt),
        "image_max_dimension": None,
        "number_of_images_sent": 0,
        "estimated_payload_size_bytes": len(prompt.encode("utf-8")),
        "request_type": "text_reextract",
        "used_image_input": False,
        "document_type_hint": selected_type,
        "reused_extraction_context": True,
    }

    try:
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "document_reextract",
                    "schema": response_schema,
                    "strict": True,
                }
            },
        )
    except OpenAIError as exc:
        raise OpenAIExtractionError("OpenAI re-extraction request failed.") from exc

    raw_text = getattr(response, "output_text", None)
    if not raw_text:
        raise OpenAIExtractionError("OpenAI returned an empty response.")

    token_usage = safe_get_token_usage(response)
    cost_data = calculate_openai_cost(token_usage, model)
    extracted_data = _normalize_document_data(_parse_json(raw_text))
    optimization["schema_mode"] = "simplified_document_specific"
    optimization["document_type"] = extracted_data["document_type"]
    _attach_request_metadata(cost_data, optimization)

    return extracted_data, cost_data, optimization


def _parse_json(raw_text):
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise OpenAIExtractionError("OpenAI returned invalid JSON.") from exc

    if not isinstance(parsed, dict):
        raise OpenAIExtractionError("OpenAI response JSON must be an object.")

    return parsed


def _build_optimization_metadata(prompt, prompt_mode, image_data_urls, image_metadata):
    metadata = image_metadata if isinstance(image_metadata, list) else []
    first_image_metadata = metadata[0] if metadata else {}
    image_max_dimension = first_image_metadata.get("max_dimension")
    estimated_payload_size_bytes = len(prompt.encode("utf-8")) + sum(len(image_url) for image_url in image_data_urls)

    return {
        "prompt_mode": prompt_mode,
        "prompt_character_length": len(prompt),
        "image_max_dimension": image_max_dimension,
        "number_of_images_sent": len(image_data_urls),
        "estimated_payload_size_bytes": estimated_payload_size_bytes,
    }


def _attach_request_metadata(cost_data, optimization):
    cost_data["request_type"] = optimization["request_type"]
    cost_data["used_image_input"] = optimization["used_image_input"]
    cost_data["document_type_hint"] = optimization["document_type_hint"]
    cost_data["reused_extraction_context"] = optimization["reused_extraction_context"]


def _log_safe_request_debug(model, optimization, image_metadata):
    if os.getenv("FLASK_ENV") != "development":
        return

    metadata = image_metadata if isinstance(image_metadata, list) else []
    dimensions = [
        {
            "width": item.get("processed_width"),
            "height": item.get("processed_height"),
            "format": item.get("processed_format"),
        }
        for item in metadata
        if isinstance(item, dict)
    ]
    print(
        "OpenAI request debug:",
        {
            "model": model,
            "prompt_mode": optimization["prompt_mode"],
            "prompt_character_length": optimization["prompt_character_length"],
            "number_of_images_sent": optimization["number_of_images_sent"],
            "estimated_payload_size_bytes": optimization["estimated_payload_size_bytes"],
            "processed_images": dimensions,
        },
    )


def _normalize_document_data(payload):
    if _looks_like_old_receipt_schema(payload):
        return _wrap_old_receipt_schema(payload)

    document_type = payload.get("document_type")
    if document_type not in DOCUMENT_TYPES:
        document_type = "unknown"

    data = payload.get("data")
    if not isinstance(data, dict):
        data = {}

    warnings = payload.get("warnings")
    if not isinstance(warnings, list):
        warnings = []

    if document_type == "unknown" and "Document type is unknown. Please review manually." not in warnings:
        warnings.append("Document type is unknown. Please review manually.")

    normalized = {
        "document_type": document_type,
        "data": _normalize_data_for_type(document_type, data),
        "extraction_context": _normalize_extraction_context(payload.get("extraction_context")),
        "warnings": [str(warning) for warning in warnings if warning],
    }

    if document_type == "unknown":
        normalized["common"] = _normalize_unknown_common(payload.get("common"))

    return normalized


def _looks_like_old_receipt_schema(payload):
    return "document_type" not in payload and (
        "vendor_name" in payload or "receipt_date" in payload or "total_amount" in payload or "items" in payload
    )


def _wrap_old_receipt_schema(payload):
    warnings = payload.get("warnings") if isinstance(payload.get("warnings"), list) else []
    data = dict(payload)
    data.pop("warnings", None)
    return {
        "document_type": "receipt",
        "data": _normalize_data_for_type("receipt", data),
        "extraction_context": _normalize_extraction_context(payload.get("extraction_context")),
        "warnings": [str(warning) for warning in warnings if warning],
    }


def _normalize_extraction_context(context):
    if not isinstance(context, dict):
        return None
    return {
        "raw_text": context.get("raw_text") or "",
        "key_value_text": context.get("key_value_text") or "",
        "tables_text": context.get("tables_text") or "",
    }


def _normalize_data_for_type(document_type, data):
    if document_type == "unknown":
        return _normalize_unknown_data(data)

    field_names = _fields_for_document_type(document_type)
    normalized = {field_name: data.get(field_name) for field_name in field_names}

    items = normalized.get("items")
    normalized["items"] = _normalize_items(document_type, items)
    return normalized


def _normalize_unknown_common(common):
    source = common if isinstance(common, dict) else {}
    return {
        "source_name": source.get("source_name"),
        "recipient_name": source.get("recipient_name"),
        "document_date": source.get("document_date"),
        "document_number": source.get("document_number"),
        "reference_number": source.get("reference_number"),
        "currency": source.get("currency"),
    }


def _normalize_unknown_data(data):
    source = data if isinstance(data, dict) else {}
    key_values = source.get("key_values")
    items = source.get("items")
    return {
        "visible_title": source.get("visible_title"),
        "summary": source.get("summary"),
        "key_values": _normalize_unknown_key_values(key_values),
        "items": _normalize_unknown_items(items),
    }


def _normalize_unknown_key_values(key_values):
    if not isinstance(key_values, list):
        return []
    return [
        {
            "label": item.get("label"),
            "value": item.get("value"),
        }
        for item in key_values
        if isinstance(item, dict)
    ]


def _normalize_unknown_items(items):
    if not isinstance(items, list):
        return []
    return [
        {
            "description": item.get("description"),
            "quantity": item.get("quantity"),
            "unit": item.get("unit"),
            "unit_price": item.get("unit_price", item.get("amount")),
            "line_total": item.get("line_total", item.get("total")),
            "remarks": item.get("remarks"),
        }
        for item in items
        if isinstance(item, dict)
    ]


def _fields_for_document_type(document_type):
    return {
        "receipt": [
            "vendor_name",
            "receipt_date",
            "receipt_number",
            "payment_method",
            "subtotal",
            "tax_sst_amount",
            "total_amount",
            "currency",
            "category",
            "items",
        ],
        "invoice": [
            "vendor_name",
            "customer_name",
            "invoice_number",
            "invoice_date",
            "due_date",
            "subtotal",
            "tax_sst_amount",
            "total_amount",
            "currency",
            "items",
        ],
        "payment_receipt": [
            "vendor_name",
            "payer_name",
            "receipt_number",
            "payment_date",
            "reference_number",
            "payment_method",
            "total_amount_received",
            "currency",
            "items",
        ],
        "delivery_order": [
            "vendor_name",
            "delivery_order_number",
            "delivery_date",
            "customer_name",
            "customer_po_number",
            "deliver_to",
            "items",
        ],
        "unknown": [
            "visible_title",
            "summary",
            "key_values",
            "items",
        ],
    }.get(document_type, [])


def _normalize_items(document_type, items):
    if not isinstance(items, list):
        return []
    return [_normalize_item(document_type, item) for item in items if isinstance(item, dict)]


def _normalize_item(document_type, item):
    if document_type == "receipt":
        return {
            "name": item.get("name"),
            "quantity": item.get("quantity"),
            "unit_price": item.get("unit_price", item.get("amount")),
            "line_total": item.get("line_total", item.get("total")),
        }
    if document_type in {"invoice", "payment_receipt"}:
        if document_type == "payment_receipt":
            return {
                "invoice_number": item.get("invoice_number"),
                "description": item.get("description"),
                "line_total": item.get("line_total", item.get("total")),
            }
        normalized = {
            "name": item.get("name"),
            "quantity": item.get("quantity"),
            "unit": item.get("unit"),
            "unit_price": item.get("unit_price", item.get("amount")),
            "line_total": item.get("line_total", item.get("total")),
        }
        return normalized
    if document_type == "delivery_order":
        return {
            "item_code": item.get("item_code"),
            "description": item.get("description"),
            "quantity": item.get("quantity"),
            "unit": item.get("unit"),
            "remarks": item.get("remarks"),
        }
    return item
