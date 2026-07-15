import base64
import io
import os

from PIL import Image, ImageEnhance, ImageOps, ImageStat

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None


DEFAULT_MAX_IMAGE_DIMENSION = 1200
DEFAULT_IMAGE_JPEG_QUALITY = 80
DEFAULT_PREPROCESS_MODE = "auto"
DEFAULT_MIN_CROP_CONFIDENCE = 0.85
DEFAULT_CROP_PADDING_RATIO = 0.08
DEFAULT_CROP_MIN_AREA_RATIO = 0.50
DEFAULT_SCANNER_CROP_MODE = "conservative"
CLOSE_SCORE_MARGIN = 5.0


def process_image_for_openai(file_path):
    with Image.open(file_path) as image:
        return process_pil_image_for_openai(image)


def process_pil_image_for_openai(image):
    max_dimension = _get_int_env("MAX_IMAGE_DIMENSION", DEFAULT_MAX_IMAGE_DIMENSION)
    jpeg_quality = _get_int_env("IMAGE_JPEG_QUALITY", DEFAULT_IMAGE_JPEG_QUALITY)
    preprocess_mode = os.getenv("IMAGE_PREPROCESS_MODE", DEFAULT_PREPROCESS_MODE).strip().lower()

    oriented_image = ImageOps.exif_transpose(image).convert("RGB")
    original_width, original_height = oriented_image.size

    cropped_image, crop_metadata = _auto_crop(oriented_image)
    candidates = _build_candidates(cropped_image)
    selected_mode, selected_image, candidate_scores = _select_candidate(candidates, preprocess_mode)
    processed_image = _resize_image(selected_image, max_dimension)
    processed_width, processed_height = processed_image.size

    data_url = _to_jpeg_data_url(processed_image, jpeg_quality)
    metadata = {
        "selected_preprocessing_mode": selected_mode,
        "original_width": original_width,
        "original_height": original_height,
        "processed_width": processed_width,
        "processed_height": processed_height,
        "processed_format": "JPEG",
        "jpeg_quality": jpeg_quality,
        "max_dimension": max_dimension,
        "crop": crop_metadata,
    }

    if _get_bool_env("SHOW_PREPROCESS_DEBUG", False):
        metadata["candidate_scores"] = candidate_scores

    return {
        "openai_image_url": data_url,
        "preview_image_url": data_url,
        "metadata": metadata,
    }


def image_to_data_url(file_path):
    return process_image_for_openai(file_path)["openai_image_url"]


def pil_image_to_data_url(image, jpeg_quality=None):
    quality = jpeg_quality if jpeg_quality is not None else _get_int_env("IMAGE_JPEG_QUALITY", DEFAULT_IMAGE_JPEG_QUALITY)
    return _to_jpeg_data_url(image.convert("RGB"), quality)


def should_return_image_preview():
    return _get_bool_env("RETURN_IMAGE_PREVIEW", True)


def _auto_crop(image):
    if not _get_bool_env("AUTO_CROP_RECEIPT", True):
        return image, _crop_metadata(False, "none", 0.0, "Automatic crop is disabled")

    min_confidence = _get_float_env("MIN_CROP_CONFIDENCE", DEFAULT_MIN_CROP_CONFIDENCE)
    padding_ratio = _get_float_env("CROP_PADDING_RATIO", DEFAULT_CROP_PADDING_RATIO)
    min_area_ratio = _get_float_env("CROP_MIN_AREA_RATIO", DEFAULT_CROP_MIN_AREA_RATIO)
    scanner_mode = os.getenv("SCANNER_CROP_MODE", DEFAULT_SCANNER_CROP_MODE).strip().lower()
    conservative_crop = scanner_mode != "off" and _get_bool_env("CONSERVATIVE_CROP", True)
    enable_perspective = _get_bool_env("ENABLE_PERSPECTIVE_CORRECTION", True)

    if cv2 is None or np is None:
        return image, _crop_metadata(False, "none", 0.0, "OpenCV is not available")

    try:
        crop_result = scanner_auto_crop(
            image,
            min_confidence=min_confidence,
            padding_ratio=padding_ratio,
            min_area_ratio=min_area_ratio,
            conservative_crop=conservative_crop,
            enable_perspective=enable_perspective,
        )
    except Exception:
        return image, _crop_metadata(False, "none", 0.0, "Document crop detection failed")

    cropped_image, metadata = crop_result
    return cropped_image, metadata


def scanner_auto_crop(image, min_confidence, padding_ratio, min_area_ratio, conservative_crop, enable_perspective):
    candidates = detect_document_boundary(image)

    if not candidates:
        return image, _crop_metadata(False, "none", 0.0, "No document boundary found")

    best_rejected = None
    valid_candidates = []

    for candidate in candidates:
        padded_box = apply_safe_padding(candidate["box"], image.width, image.height, padding_ratio)
        confidence = _score_document_boundary(candidate, padded_box, image.width, image.height)
        rejection_reason = validate_document_crop(
            candidate,
            padded_box,
            confidence,
            min_confidence,
            min_area_ratio,
            image.width,
            image.height,
            conservative_crop,
        )

        if rejection_reason:
            best_rejected = _best_rejected(best_rejected, confidence, rejection_reason)
            continue

        valid_candidates.append((confidence, candidate, padded_box))

    if not valid_candidates:
        confidence = best_rejected["confidence"] if best_rejected else 0.0
        reason = (
            best_rejected["reason"]
            if best_rejected
            else "Rejected because detected contour may be inner content/table instead of outer paper"
        )
        return image, _crop_metadata(False, "none", confidence, reason, perspective_corrected=False)

    confidence, candidate, padded_box = max(valid_candidates, key=lambda item: item[0])
    cropped_image, method, perspective_corrected = _apply_document_crop(image, candidate, padded_box, enable_perspective)

    metadata = _crop_metadata(
        True,
        method,
        confidence,
        crop_box=padded_box,
        padding_ratio=padding_ratio,
        perspective_corrected=perspective_corrected,
    )
    metadata["crop_strategy"] = candidate["strategy"]
    return cropped_image, metadata


def detect_document_boundary(image):
    rgb = np.array(image)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    edge_map = _edge_map(gray)
    candidates = []

    candidates.extend(_contour_candidates(edge_map, image.width, image.height, "edge_contour"))
    candidates.extend(_bright_paper_mask_candidates(rgb, image.width, image.height))
    candidates.extend(_rectangular_threshold_candidates(gray, image.width, image.height))
    candidates.extend(_paper_region_box_candidates(rgb, image.width, image.height))

    return sorted(candidates, key=lambda candidate: candidate["area_ratio"], reverse=True)[:20]


def _edge_map(gray):
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 40, 140)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    return cv2.dilate(closed_edges, kernel, iterations=1)


def _contour_candidates(binary_image, image_width, image_height, strategy):
    contours, _hierarchy = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    image_area = image_width * image_height

    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:12]:
        candidate = _candidate_from_contour(contour, image_width, image_height, image_area, strategy)
        if candidate:
            candidates.append(candidate)

    return candidates


def _bright_paper_mask_candidates(rgb, image_width, image_height):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    mask = cv2.inRange(value, 150, 255)
    low_saturation_mask = cv2.inRange(saturation, 0, 95)
    mask = cv2.bitwise_and(mask, low_saturation_mask)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.dilate(mask, kernel, iterations=1)
    return _contour_candidates(mask, image_width, image_height, "bright_paper_mask")


def _rectangular_threshold_candidates(gray, image_width, image_height):
    threshold = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        41,
        9,
    )
    threshold = cv2.bitwise_not(threshold)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    threshold = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel, iterations=2)
    return _contour_candidates(threshold, image_width, image_height, "rectangular_threshold")


def _paper_region_box_candidates(rgb, image_width, image_height):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    value = hsv[:, :, 2]
    mask = cv2.inRange(value, 120, 255)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return []

    largest = max(contours, key=cv2.contourArea)
    candidate = _candidate_from_contour(largest, image_width, image_height, image_width * image_height, "paper_region_box")
    return [candidate] if candidate else []


def _candidate_from_contour(contour, image_width, image_height, image_area, strategy):
    contour_area = cv2.contourArea(contour)
    area_ratio = contour_area / image_area if image_area else 0
    if area_ratio < 0.15 or area_ratio > 0.995:
        return None

    x, y, width, height = cv2.boundingRect(contour)
    if not _is_reasonable_crop_box(width, height, image_width, image_height):
        return None

    perimeter = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.025 * perimeter, True) if perimeter else contour
    rectangularity = contour_area / max(width * height, 1)

    return {
        "strategy": strategy,
        "contour": contour,
        "approx": approx,
        "corner_count": len(approx),
        "box": _box(x, y, width, height),
        "area_ratio": area_ratio,
        "rectangularity": rectangularity,
        "perimeter_ratio": perimeter / max(2 * (width + height), 1),
    }


def _build_candidates(image):
    color = image.convert("RGB")

    enhanced = ImageEnhance.Contrast(color).enhance(1.15)
    enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.15)

    gray = ImageOps.grayscale(color)
    gray = ImageEnhance.Contrast(gray).enhance(1.20).convert("RGB")

    threshold = _adaptive_threshold(color)

    return {
        "original_color": color,
        "enhanced_color": enhanced,
        "grayscale": gray,
        "adaptive_threshold": threshold,
    }


def _select_candidate(candidates, preprocess_mode):
    scores = {name: round(_score_candidate(image, name), 2) for name, image in candidates.items()}

    if preprocess_mode in candidates and preprocess_mode != "auto":
        return preprocess_mode, candidates[preprocess_mode], scores

    highest_mode = max(scores, key=scores.get)
    highest_score = scores[highest_mode]

    for preferred_mode in ("enhanced_color", "original_color", "grayscale"):
        if scores[preferred_mode] >= highest_score - CLOSE_SCORE_MARGIN:
            return preferred_mode, candidates[preferred_mode], scores

    return highest_mode, candidates[highest_mode], scores


def _score_candidate(image, mode):
    gray = ImageOps.grayscale(image)
    stat = ImageStat.Stat(gray)
    brightness = stat.mean[0]
    contrast = stat.stddev[0]
    histogram = gray.histogram()
    pixel_count = max(1, gray.width * gray.height)
    black_ratio = sum(histogram[:8]) / pixel_count
    white_ratio = sum(histogram[248:]) / pixel_count
    harsh_ratio = black_ratio + white_ratio

    sharpness = _laplacian_variance(gray)
    brightness_penalty = abs(brightness - 145) * 0.12
    harsh_penalty = harsh_ratio * 45
    score = 45 + min(contrast, 80) * 0.55 + min(sharpness, 900) * 0.025
    score -= brightness_penalty + harsh_penalty

    if brightness < 55 or brightness > 225:
        score -= 18
    if mode == "adaptive_threshold":
        score -= 8 + harsh_ratio * 35
    if mode == "enhanced_color":
        score += 4
    if mode == "original_color":
        score += 2

    return max(0, min(100, score))


def _adaptive_threshold(image):
    gray = ImageOps.grayscale(image)
    if cv2 is None or np is None:
        return gray.point(lambda value: 255 if value > 180 else 0).convert("RGB")

    gray_array = np.array(gray)
    threshold = cv2.adaptiveThreshold(
        gray_array,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )
    return Image.fromarray(threshold).convert("RGB")


def _resize_image(image, max_dimension):
    resized = image.copy().convert("RGB")
    resized.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
    return resized


def _to_jpeg_data_url(image, jpeg_quality):
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=jpeg_quality, optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"


def _perspective_crop(rgb_array, points):
    rect = _order_points(points.astype("float32"))
    top_width = np.linalg.norm(rect[1] - rect[0])
    bottom_width = np.linalg.norm(rect[2] - rect[3])
    left_height = np.linalg.norm(rect[3] - rect[0])
    right_height = np.linalg.norm(rect[2] - rect[1])
    max_width = int(max(top_width, bottom_width))
    max_height = int(max(left_height, right_height))

    if max_width < 250 or max_height < 250:
        return None

    destination = np.array(
        [[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]],
        dtype="float32",
    )
    matrix = cv2.getPerspectiveTransform(rect, destination)
    return cv2.warpPerspective(rgb_array, matrix, (max_width, max_height))


def _order_points(points):
    rect = np.zeros((4, 2), dtype="float32")
    sums = points.sum(axis=1)
    diffs = np.diff(points, axis=1)
    rect[0] = points[np.argmin(sums)]
    rect[2] = points[np.argmax(sums)]
    rect[1] = points[np.argmin(diffs)]
    rect[3] = points[np.argmax(diffs)]
    return rect


def _laplacian_variance(gray_image):
    if cv2 is None or np is None:
        return ImageStat.Stat(gray_image).stddev[0]
    return float(cv2.Laplacian(np.array(gray_image), cv2.CV_64F).var())


def _is_reasonable_crop_box(width, height, image_width, image_height):
    if width < 250 or height < 250:
        return False
    if width > image_width * 0.99 and height > image_height * 0.99:
        return False
    aspect_ratio = max(width / max(height, 1), height / max(width, 1))
    return aspect_ratio <= 8


def _score_document_boundary(candidate, crop_box, image_width, image_height):
    width_ratio = crop_box["width"] / max(image_width, 1)
    height_ratio = crop_box["height"] / max(image_height, 1)
    area_ratio = (crop_box["width"] * crop_box["height"]) / max(image_width * image_height, 1)
    contour_area_ratio = candidate["area_ratio"]
    rectangularity = min(candidate["rectangularity"], 1.0)
    corner_count = candidate["corner_count"]
    aspect_ratio = max(crop_box["width"] / max(crop_box["height"], 1), crop_box["height"] / max(crop_box["width"], 1))

    left_gap = crop_box["x"] / max(image_width, 1)
    top_gap = crop_box["y"] / max(image_height, 1)
    right_gap = (image_width - (crop_box["x"] + crop_box["width"])) / max(image_width, 1)
    bottom_gap = (image_height - (crop_box["y"] + crop_box["height"])) / max(image_height, 1)
    max_edge_gap = max(left_gap, top_gap, right_gap, bottom_gap)
    edge_proximity = max(0.0, 1.0 - max_edge_gap * 3.0)

    confidence = 0.16
    confidence += min(area_ratio / 0.80, 1.0) * 0.24
    confidence += min(contour_area_ratio / 0.70, 1.0) * 0.16
    confidence += rectangularity * 0.16
    confidence += min(width_ratio / 0.80, 1.0) * 0.10
    confidence += min(height_ratio / 0.80, 1.0) * 0.10
    confidence += edge_proximity * 0.08

    if corner_count == 4:
        confidence += 0.10
    elif 4 < corner_count <= 8:
        confidence += 0.04
    else:
        confidence -= 0.08

    if aspect_ratio > 6.5:
        confidence -= 0.12
    if width_ratio < 0.70:
        confidence -= 0.10
    if height_ratio < 0.70:
        confidence -= 0.10
    if top_gap > 0.10:
        confidence -= 0.12
    if bottom_gap > 0.10:
        confidence -= 0.12
    if candidate["strategy"] == "paper_region_box":
        confidence -= 0.04

    return max(0.0, min(0.98, confidence))


def validate_document_crop(
    candidate,
    crop_box,
    confidence,
    min_confidence,
    min_area_ratio,
    image_width,
    image_height,
    conservative_crop,
):
    width_ratio = crop_box["width"] / max(image_width, 1)
    height_ratio = crop_box["height"] / max(image_height, 1)
    crop_area_ratio = (crop_box["width"] * crop_box["height"]) / max(image_width * image_height, 1)
    top_removed_ratio = crop_box["y"] / max(image_height, 1)
    bottom_removed_ratio = (image_height - (crop_box["y"] + crop_box["height"])) / max(image_height, 1)
    rectangularity = candidate["rectangularity"]

    if confidence < min_confidence:
        return "Rejected because crop confidence is below threshold and may exclude document edges"
    if crop_area_ratio < min_area_ratio or candidate["area_ratio"] < min_area_ratio * 0.85:
        return "Rejected because detected region is too small to be the full document"
    if rectangularity < 0.35:
        return "Rejected because detected contour is not document-like"

    if conservative_crop:
        if width_ratio < 0.70:
            return "Rejected because detected region is too narrow and may be an inner table"
        if height_ratio < 0.70:
            return "Rejected because detected region is too short and may exclude header or footer"
        if top_removed_ratio > 0.10:
            return "Rejected because crop removes too much from the top of the document"
        if bottom_removed_ratio > 0.10:
            return "Rejected because crop removes too much from the bottom of the document"

    return None


def _apply_document_crop(image, candidate, crop_box, enable_perspective):
    if enable_perspective and _has_reliable_corners(candidate):
        transformed = _perspective_crop(np.array(image), candidate["approx"].reshape(4, 2))
        if transformed is not None:
            corrected = Image.fromarray(transformed).convert("RGB")
            return corrected, "document_boundary_perspective", True

    cropped = image.crop(
        (
            crop_box["x"],
            crop_box["y"],
            crop_box["x"] + crop_box["width"],
            crop_box["y"] + crop_box["height"],
        )
    )
    return cropped.convert("RGB"), "document_boundary_rectangular", False


def _has_reliable_corners(candidate):
    return (
        candidate["corner_count"] == 4
        and candidate["area_ratio"] >= 0.50
        and candidate["rectangularity"] >= 0.55
        and candidate["strategy"] in {"edge_contour", "bright_paper_mask", "rectangular_threshold"}
    )


def apply_safe_padding(box, image_width, image_height, padding_ratio):
    padding = max(32, int(min(image_width, image_height) * padding_ratio))
    left = max(0, box["x"] - padding)
    top = max(0, box["y"] - padding)
    right = min(image_width, box["x"] + box["width"] + padding)
    bottom = min(image_height, box["y"] + box["height"] + padding)
    return _box(left, top, right - left, bottom - top)


def _score_crop_candidate(x, y, width, height, area_ratio, corner_count, image_width, image_height):
    width_ratio = width / max(image_width, 1)
    height_ratio = height / max(image_height, 1)
    left_gap = x / max(image_width, 1)
    top_gap = y / max(image_height, 1)
    right_gap = (image_width - (x + width)) / max(image_width, 1)
    bottom_gap = (image_height - (y + height)) / max(image_height, 1)
    edge_gap = max(0, left_gap) + max(0, top_gap) + max(0, right_gap) + max(0, bottom_gap)
    edge_score = max(0, 1 - edge_gap)
    quad_bonus = 0.10 if corner_count == 4 else 0.03

    confidence = 0.20
    confidence += min(area_ratio / 0.75, 1) * 0.28
    confidence += min(width_ratio / 0.80, 1) * 0.17
    confidence += min(height_ratio / 0.80, 1) * 0.17
    confidence += edge_score * 0.10
    confidence += quad_bonus

    if width_ratio < 0.70:
        confidence -= 0.12
    if height_ratio < 0.70:
        confidence -= 0.12
    if top_gap > 0.12:
        confidence -= 0.10
    if bottom_gap > 0.12:
        confidence -= 0.10

    return max(0.0, min(0.98, confidence))


def _crop_rejection_reason(
    crop_box,
    area_ratio,
    confidence,
    min_confidence,
    min_area_ratio,
    image_width,
    image_height,
    conservative_crop,
):
    width_ratio = crop_box["width"] / max(image_width, 1)
    height_ratio = crop_box["height"] / max(image_height, 1)
    crop_area_ratio = (crop_box["width"] * crop_box["height"]) / max(image_width * image_height, 1)
    top_removed_ratio = crop_box["y"] / max(image_height, 1)
    bottom_removed_ratio = (image_height - (crop_box["y"] + crop_box["height"])) / max(image_height, 1)

    if confidence < min_confidence:
        return f"Rejected: confidence below {min_confidence:.2f} and crop may exclude document edges"
    if crop_area_ratio < min_area_ratio or area_ratio < min_area_ratio:
        return "Rejected: detected region is too small to be the full document"

    if conservative_crop:
        if width_ratio < 0.70:
            return "Rejected: detected region is too narrow and may be an inner table or text block"
        if height_ratio < 0.70:
            return "Rejected: detected region is too short and may exclude header or footer content"
        if top_removed_ratio > 0.10:
            return "Rejected: crop removes too much from the top of the document"
        if bottom_removed_ratio > 0.10:
            return "Rejected: crop removes too much from the bottom of the document"

    return None


def _best_rejected(current, confidence, reason):
    if current is None or confidence > current["confidence"]:
        return {"confidence": confidence, "reason": reason}
    return current


def _padded_box(x, y, width, height, image_width, image_height, padding_ratio):
    padding = max(40, int(min(image_width, image_height) * padding_ratio))
    left = max(0, x - padding)
    top = max(0, y - padding)
    right = min(image_width, x + width + padding)
    bottom = min(image_height, y + height + padding)
    return _box(left, top, right - left, bottom - top)


def _box(x, y, width, height):
    return {"x": int(x), "y": int(y), "width": int(width), "height": int(height)}


def _crop_metadata(applied, method, confidence, reason=None, crop_box=None, padding_ratio=None, perspective_corrected=False):
    metadata = {
        "crop_applied": applied,
        "crop_method": method,
        "crop_confidence": round(float(confidence), 2),
        "perspective_corrected": bool(perspective_corrected),
    }
    if crop_box:
        metadata["crop_box"] = crop_box
    if padding_ratio is not None:
        metadata["crop_padding_ratio"] = round(float(padding_ratio), 2)
    if reason:
        metadata["crop_reason"] = reason
    return metadata


def _get_int_env(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _get_float_env(name, default):
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _get_bool_env(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}
