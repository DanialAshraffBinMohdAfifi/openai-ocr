import os

from PIL import Image

try:
    import fitz
except ImportError:
    fitz = None


DEFAULT_MAX_PDF_PAGES = 1
DEFAULT_PDF_RENDER_DPI = 200


class PDFProcessingError(Exception):
    pass


def render_pdf_to_images(pdf_path, max_pages=None, dpi=None):
    if fitz is None:
        raise PDFProcessingError("Unable to process PDF. PyMuPDF is not installed.")

    max_pages = max_pages if max_pages is not None else _get_int_env("MAX_PDF_PAGES", DEFAULT_MAX_PDF_PAGES)
    dpi = dpi if dpi is not None else _get_int_env("PDF_RENDER_DPI", DEFAULT_PDF_RENDER_DPI)
    pdf_warnings = []

    try:
        document = fitz.open(pdf_path)
    except Exception as exc:
        raise PDFProcessingError("Unable to process PDF. The file may be encrypted, corrupted, or empty.") from exc

    try:
        if document.needs_pass:
            raise PDFProcessingError("Unable to process PDF. The file is password-protected.")

        total_pages = document.page_count
        if total_pages <= 0:
            raise PDFProcessingError("Unable to process PDF. The file has no pages.")

        processed_pages = min(total_pages, max_pages)
        if total_pages > processed_pages:
            pdf_warnings.append(f"PDF has {total_pages} pages. Only first {processed_pages} pages were processed.")

        images = []
        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)

        for page_index in range(processed_pages):
            try:
                page = document.load_page(page_index)
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                images.append(image)
            except Exception as exc:
                raise PDFProcessingError("Unable to process PDF. A page could not be rendered.") from exc

        metadata = {
            "is_pdf": True,
            "total_pdf_pages": total_pages,
            "processed_pdf_pages": len(images),
            "pdf_render_dpi": dpi,
            "pdf_warnings": pdf_warnings,
        }
        return images, metadata
    finally:
        document.close()


def _get_int_env(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default
