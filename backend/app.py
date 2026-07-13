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
    save_upload,
)
from services.image_service import process_image_for_openai, should_return_image_preview
from services.openai_service import OpenAIExtractionError, extract_receipt_data
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

    @app.post("/api/extract")
    def extract():
        started_at = time.perf_counter()
        saved_path = None

        try:
            if "file" not in request.files:
                processing_time_ms = elapsed_ms(started_at)
                return error_response("Missing file field named 'file'.", 400, processing_time_ms)

            uploaded_file = request.files["file"]
            saved_path, original_filename = save_upload(uploaded_file)
            processed_image = process_image_for_openai(saved_path)
            image_data_url = processed_image["openai_image_url"]

            extracted_data, usage = extract_receipt_data(image_data_url)
            validation = validate_receipt_data(extracted_data)
            processing_time_ms = elapsed_ms(started_at)
            image_preview = build_image_preview(saved_path, processed_image)

            return jsonify(
                {
                    "success": True,
                    "filename": original_filename,
                    "data": extracted_data,
                    "validation": validation,
                    "usage": usage,
                    "image_preview": image_preview,
                    "processing_time_ms": processing_time_ms,
                }
            )
        except FileValidationError as exc:
            processing_time_ms = elapsed_ms(started_at)
            return error_response(str(exc), 400, processing_time_ms)
        except OpenAIExtractionError as exc:
            processing_time_ms = elapsed_ms(started_at)
            return error_response(str(exc), 502, processing_time_ms)
        except Exception:
            app.logger.exception("Unexpected extraction failure")
            processing_time_ms = elapsed_ms(started_at)
            return error_response("Receipt extraction failed. Please try again.", 500, processing_time_ms)
        finally:
            cleanup_file(saved_path)

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


def build_image_preview(saved_path, processed_image):
    if not should_return_image_preview():
        return None

    return {
        "original_image_url": original_image_to_data_url(saved_path),
        "processed_image_url": processed_image["preview_image_url"],
        "metadata": processed_image["metadata"],
    }


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_ENV") == "development")
