import base64
import mimetypes
import os
import tempfile
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_PDF_MIME_TYPES = {"application/pdf", "application/x-pdf"}


class FileValidationError(Exception):
    pass


def save_upload(uploaded_file):
    if not uploaded_file or not uploaded_file.filename:
        raise FileValidationError("No file selected.")

    original_filename = secure_filename(uploaded_file.filename)
    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS | {".pdf"}:
        raise FileValidationError("Unsupported file type. Upload a JPG, JPEG, PNG, WEBP, or PDF file.")

    content_type = (uploaded_file.mimetype or "").lower()
    if content_type and content_type != "application/octet-stream" and content_type not in ALLOWED_MIME_TYPES | ALLOWED_PDF_MIME_TYPES:
        raise FileValidationError("Unsupported MIME type. Upload a valid receipt image or PDF.")

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=extension)
    temp_file.close()
    uploaded_file.save(temp_file.name)

    if os.path.getsize(temp_file.name) == 0:
        cleanup_file(temp_file.name)
        raise FileValidationError("Uploaded file is empty.")

    if extension == ".pdf":
        _verify_pdf(temp_file.name)
    else:
        _verify_image(temp_file.name)
    return temp_file.name, original_filename


def image_to_data_url(file_path):
    mime_type = _detect_mime_type(file_path)
    with open(file_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def cleanup_file(file_path):
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass


def is_pdf_file(file_path):
    return Path(file_path).suffix.lower() == ".pdf"


def _verify_image(file_path):
    try:
        with Image.open(file_path) as image:
            image.verify()
            if image.format not in {"JPEG", "PNG", "WEBP"}:
                raise FileValidationError("Unsupported image content. Upload a JPG, JPEG, PNG, or WEBP image.")
    except UnidentifiedImageError as exc:
        raise FileValidationError("Invalid image file.") from exc


def _verify_pdf(file_path):
    with open(file_path, "rb") as pdf_file:
        header = pdf_file.read(5)
    if header != b"%PDF-":
        raise FileValidationError("Invalid PDF file.")


def _detect_mime_type(file_path):
    mime_type, _encoding = mimetypes.guess_type(file_path)
    if mime_type not in ALLOWED_MIME_TYPES:
        raise FileValidationError("Could not detect a supported image MIME type.")
    return mime_type
