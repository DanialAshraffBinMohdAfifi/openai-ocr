import os
import time
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from services.file_service import (
    FileValidationError,
    cleanup_file,
    image_to_data_url as original_image_to_data_url,
    is_pdf_file,
    save_upload,
)
from services.cost_log_service import append_cost_log, read_cost_log, read_cost_summary, reset_cost_log
from services.image_service import pil_image_to_data_url, process_image_for_openai, process_pil_image_for_openai, should_return_image_preview
from services.openai_service import OpenAIExtractionError, extract_receipt_data, reextract_receipt_data
from services.pdf_service import PDFProcessingError, render_pdf_to_images
from services.validation_service import validate_receipt_data


def create_app():
    app = Flask(__name__)
    CORS(app)

    print("OPENAI_API_KEY configured:", bool(os.getenv("OPENAI_API_KEY")))

    max_upload_mb = int(os.getenv("MAX_UPLOAD_MB", "10"))
    app.config["MAX_CONTENT_LENGTH"] = max_upload_mb * 1024 * 1024

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/api/cost-summary")
    def cost_summary():
        return jsonify({"success": True, "summary": read_cost_summary()})

    @app.get("/api/cost-log")
    def cost_log():
        limit = parse_limit(request.args.get("limit"), default=50, maximum=500)
        return jsonify({"success": True, "records": read_cost_log(limit)})

    @app.delete("/api/cost-log")
    def clear_cost_log():
        if os.getenv("FLASK_ENV") == "production":
            return error_response("Cost log reset is disabled in production.", 403)

        reset_cost_log()
        return jsonify({"success": True, "message": "Testing cost log reset."})

    @app.post("/api/extract")
    def extract():
        started_at = time.perf_counter()
        saved_path = None
        original_filename = ""
        file_type = ""
        usage = None

        try:
            if "file" not in request.files:
                processing_time_ms = elapsed_ms(started_at)
                log_cost_attempt(app, original_filename, file_type, usage, processing_time_ms, False, "Missing file field named 'file'.")
                return error_response("Missing file field named 'file'.", 400, processing_time_ms)

            document_type_hint = parse_document_type_hint(request.form.get("document_type_hint"))
            uploaded_file = request.files["file"]
            saved_path, original_filename = save_upload(uploaded_file)
            file_type = "pdf" if is_pdf_file(saved_path) else "image"
            processed_images, image_preview, pdf_metadata = prepare_openai_images(saved_path)
            image_data_urls = [processed_image["openai_image_url"] for processed_image in processed_images]

            image_metadata = [processed_image["metadata"] for processed_image in processed_images]
            extracted_data, usage, optimization = extract_receipt_data(image_data_urls, image_metadata, document_type_hint)
            validation = validate_receipt_data(extracted_data)
            processing_time_ms = elapsed_ms(started_at)
            log_cost_attempt(app, original_filename, file_type, usage, processing_time_ms, True)

            return jsonify(
                {
                    "success": True,
                    "filename": original_filename,
                    "data": extracted_data,
                    "validation": validation,
                    "usage": usage,
                    "image_preview": image_preview,
                    "pdf": pdf_metadata,
                    "optimization": optimization,
                    "processing_time_ms": processing_time_ms,
                }
            )
        except FileValidationError as exc:
            processing_time_ms = elapsed_ms(started_at)
            log_cost_attempt(app, original_filename, file_type, usage, processing_time_ms, False, str(exc))
            return error_response(str(exc), 400, processing_time_ms)
        except PDFProcessingError as exc:
            processing_time_ms = elapsed_ms(started_at)
            log_cost_attempt(app, original_filename, file_type, usage, processing_time_ms, False, str(exc))
            return error_response(str(exc), 400, processing_time_ms)
        except OpenAIExtractionError as exc:
            processing_time_ms = elapsed_ms(started_at)
            log_cost_attempt(app, original_filename, file_type, usage, processing_time_ms, False, str(exc))
            return error_response(str(exc), 502, processing_time_ms)
        except Exception:
            app.logger.exception("Unexpected extraction failure")
            processing_time_ms = elapsed_ms(started_at)
            safe_message = "Receipt extraction failed. Please try again."
            log_cost_attempt(app, original_filename, file_type, usage, processing_time_ms, False, safe_message)
            return error_response(safe_message, 500, processing_time_ms)
        finally:
            cleanup_file(saved_path)

    @app.post("/api/reextract")
    def reextract():
        started_at = time.perf_counter()
        usage = None

        try:
            payload = request.get_json(silent=True) or {}
            document_type = parse_specific_document_type(payload.get("document_type"))
            extraction_context = payload.get("extraction_context")

            if not isinstance(extraction_context, dict):
                processing_time_ms = elapsed_ms(started_at)
                return error_response("Re-extraction text is unavailable. Please scan the document again.", 400, processing_time_ms)

            extracted_data, usage, optimization = reextract_receipt_data(document_type, extraction_context)
            validation = validate_receipt_data(extracted_data)
            processing_time_ms = elapsed_ms(started_at)
            log_cost_attempt(app, "text-reextract", "text", usage, processing_time_ms, True)

            return jsonify(
                {
                    "success": True,
                    "filename": "text-reextract",
                    "data": extracted_data,
                    "validation": validation,
                    "usage": usage,
                    "image_preview": None,
                    "pdf": {"is_pdf": False},
                    "optimization": optimization,
                    "processing_time_ms": processing_time_ms,
                }
            )
        except OpenAIExtractionError as exc:
            processing_time_ms = elapsed_ms(started_at)
            log_cost_attempt(app, "text-reextract", "text", usage, processing_time_ms, False, str(exc))
            return error_response(str(exc), 502, processing_time_ms)
        except Exception:
            app.logger.exception("Unexpected re-extraction failure")
            processing_time_ms = elapsed_ms(started_at)
            safe_message = "Document re-extraction failed. Please try again."
            log_cost_attempt(app, "text-reextract", "text", usage, processing_time_ms, False, safe_message)
            return error_response(safe_message, 500, processing_time_ms)

    @app.errorhandler(413)
    def file_too_large(_error):
        max_upload_mb = int(os.getenv("MAX_UPLOAD_MB", "10"))
        return error_response(f"File is too large. Maximum upload size is {max_upload_mb} MB.", 413)

    return app


def error_response(message, status_code, processing_time_ms=None):
    payload = {"success": False, "error": message}
    if processing_time_ms is not None:
        payload["processing_time_ms"] = processing_time_ms
    return jsonify(payload), status_code


def elapsed_ms(started_at):
    return round((time.perf_counter() - started_at) * 1000)


def parse_limit(value, default=50, maximum=500):
    try:
        limit = int(value or default)
    except (TypeError, ValueError):
        return default
    return max(1, min(limit, maximum))


def parse_document_type_hint(value):
    allowed = {"auto", "receipt", "invoice", "payment_receipt", "delivery_order"}
    normalized = str(value or "auto").strip().lower()
    return normalized if normalized in allowed else "auto"


def parse_specific_document_type(value):
    allowed = {"receipt", "invoice", "payment_receipt", "delivery_order"}
    normalized = str(value or "").strip().lower()
    return normalized if normalized in allowed else "receipt"


def log_cost_attempt(app, filename, file_type, usage, processing_time_ms, success, error_message=""):
    try:
        append_cost_log(filename, file_type, usage, processing_time_ms, success, error_message)
    except Exception:
        app.logger.exception("Failed to write extraction cost log")


def build_image_preview(saved_path, processed_image):
    if not should_return_image_preview():
        return None

    return {
        "original_image_url": original_image_to_data_url(saved_path),
        "processed_image_url": processed_image["preview_image_url"],
        "metadata": processed_image["metadata"],
    }


def prepare_openai_images(saved_path):
    if is_pdf_file(saved_path):
        page_images, pdf_metadata = render_pdf_to_images(saved_path)
        processed_images = [process_pil_image_for_openai(page_image) for page_image in page_images]
        image_preview = build_pdf_image_preview(page_images[0], processed_images[0], pdf_metadata)
        return processed_images, image_preview, pdf_metadata

    processed_image = process_image_for_openai(saved_path)
    image_preview = build_image_preview(saved_path, processed_image)
    return [processed_image], image_preview, {"is_pdf": False}


def build_pdf_image_preview(first_page_image, processed_image, pdf_metadata):
    if not should_return_image_preview():
        return None

    metadata = dict(processed_image["metadata"])
    metadata["source"] = "pdf"
    metadata["pdf"] = pdf_metadata

    return {
        "original_image_url": pil_image_to_data_url(first_page_image),
        "processed_image_url": processed_image["preview_image_url"],
        "metadata": metadata,
    }


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_ENV") == "development")
