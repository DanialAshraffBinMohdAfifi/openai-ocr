import csv
from datetime import datetime, timezone
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = BACKEND_DIR / "logs"
LOG_FILE = LOG_DIR / "extraction_cost_log.csv"

FIELDNAMES = [
    "timestamp",
    "filename",
    "file_type",
    "model",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "input_cost_usd",
    "output_cost_usd",
    "total_cost_usd",
    "total_cost_myr",
    "processing_time_ms",
    "request_type",
    "used_image_input",
    "document_type_hint",
    "reused_extraction_context",
    "success",
    "error_message",
]


def append_cost_log(filename, file_type, usage=None, processing_time_ms=0, success=False, error_message=""):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = LOG_FILE.exists()
    row = _build_row(filename, file_type, usage or {}, processing_time_ms, success, error_message)

    with LOG_FILE.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def read_cost_summary():
    records = _read_records()
    total_requests = len(records)
    successful_requests = sum(1 for record in records if record["success"])
    failed_requests = total_requests - successful_requests
    total_input_tokens = sum(record["input_tokens"] for record in records)
    total_output_tokens = sum(record["output_tokens"] for record in records)
    total_tokens = sum(record["total_tokens"] for record in records)
    total_cost_usd = sum(record["total_cost_usd"] for record in records)
    total_cost_myr = sum(record["total_cost_myr"] for record in records)

    return {
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost_usd, 6),
        "total_cost_myr": round(total_cost_myr, 4),
        "average_cost_usd": round(total_cost_usd / total_requests, 6) if total_requests else 0.0,
        "average_cost_myr": round(total_cost_myr / total_requests, 4) if total_requests else 0.0,
    }


def read_cost_log(limit=50):
    records = _read_records()
    return records[-limit:][::-1]


def reset_cost_log():
    if LOG_FILE.exists():
        LOG_FILE.unlink()


def _build_row(filename, file_type, usage, processing_time_ms, success, error_message):
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "filename": filename or "",
        "file_type": file_type or "",
        "model": usage.get("model", ""),
        "input_tokens": _safe_int(usage.get("input_tokens")),
        "output_tokens": _safe_int(usage.get("output_tokens")),
        "total_tokens": _safe_int(usage.get("total_tokens")),
        "input_cost_usd": _safe_float(usage.get("input_cost_usd")),
        "output_cost_usd": _safe_float(usage.get("output_cost_usd")),
        "total_cost_usd": _safe_float(usage.get("total_cost_usd")),
        "total_cost_myr": _safe_float(usage.get("total_cost_myr")),
        "processing_time_ms": _safe_int(processing_time_ms),
        "request_type": usage.get("request_type", ""),
        "used_image_input": str(bool(usage.get("used_image_input"))).lower(),
        "document_type_hint": usage.get("document_type_hint", ""),
        "reused_extraction_context": str(bool(usage.get("reused_extraction_context"))).lower(),
        "success": "true" if success else "false",
        "error_message": _safe_error_message(error_message),
    }


def _read_records():
    if not LOG_FILE.exists():
        return []

    with LOG_FILE.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return [_parse_record(row) for row in reader]


def _parse_record(row):
    return {
        "timestamp": row.get("timestamp", ""),
        "filename": row.get("filename", ""),
        "file_type": row.get("file_type", ""),
        "model": row.get("model", ""),
        "input_tokens": _safe_int(row.get("input_tokens")),
        "output_tokens": _safe_int(row.get("output_tokens")),
        "total_tokens": _safe_int(row.get("total_tokens")),
        "input_cost_usd": round(_safe_float(row.get("input_cost_usd")), 6),
        "output_cost_usd": round(_safe_float(row.get("output_cost_usd")), 6),
        "total_cost_usd": round(_safe_float(row.get("total_cost_usd")), 6),
        "total_cost_myr": round(_safe_float(row.get("total_cost_myr")), 4),
        "processing_time_ms": _safe_int(row.get("processing_time_ms")),
        "request_type": row.get("request_type", ""),
        "used_image_input": str(row.get("used_image_input", "")).lower() == "true",
        "document_type_hint": row.get("document_type_hint", ""),
        "reused_extraction_context": str(row.get("reused_extraction_context", "")).lower() == "true",
        "success": str(row.get("success", "")).lower() == "true",
        "error_message": row.get("error_message", ""),
    }


def _safe_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _safe_error_message(message):
    return str(message or "").replace("\r", " ").replace("\n", " ")[:300]
