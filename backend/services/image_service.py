import base64
import io
import os

from PIL import Image, ImageOps


DEFAULT_MAX_IMAGE_DIMENSION = 1600
DEFAULT_IMAGE_JPEG_QUALITY = 85


def process_image_for_openai(file_path):
    max_dimension = _get_int_env("MAX_IMAGE_DIMENSION", DEFAULT_MAX_IMAGE_DIMENSION)
    jpeg_quality = _get_int_env("IMAGE_JPEG_QUALITY", DEFAULT_IMAGE_JPEG_QUALITY)

    with Image.open(file_path) as image:
        original_width, original_height = image.size
        processed_image = ImageOps.exif_transpose(image)
        processed_image = processed_image.convert("RGB")
        processed_image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        processed_width, processed_height = processed_image.size

        buffer = io.BytesIO()
        processed_image.save(buffer, format="JPEG", quality=jpeg_quality, optimize=True)

    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{encoded}"

    return {
        "openai_image_url": data_url,
        "preview_image_url": data_url,
        "metadata": {
            "original_width": original_width,
            "original_height": original_height,
            "processed_width": processed_width,
            "processed_height": processed_height,
            "processed_format": "JPEG",
            "jpeg_quality": jpeg_quality,
            "max_dimension": max_dimension,
        },
    }


def image_to_data_url(file_path):
    return process_image_for_openai(file_path)["openai_image_url"]


def _get_int_env(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def should_return_image_preview():
    return os.getenv("RETURN_IMAGE_PREVIEW", "true").strip().lower() not in {"0", "false", "no", "off"}
