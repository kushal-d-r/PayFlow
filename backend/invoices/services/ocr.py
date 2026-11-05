import io
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image
from django.conf import settings


pytesseract.pytesseract.tesseract_cmd = getattr(
    settings,
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
)


def _image_to_text_and_confidence(image):
    """Read text and average Tesseract word confidence for one image."""
    result = pytesseract.image_to_data(
        image.convert("RGB"),
        lang="eng",
        output_type=pytesseract.Output.DICT,
    )
    lines = {}
    confidences = []
    for index, raw_text in enumerate(result.get("text", [])):
        word = str(raw_text).strip()
        if not word:
            continue
        key = (
            result.get("block_num", [0] * len(result["text"]))[index],
            result.get("par_num", [0] * len(result["text"]))[index],
            result.get("line_num", [0] * len(result["text"]))[index],
        )
        lines.setdefault(key, []).append(word)
        try:
            confidence = float(result.get("conf", [])[index])
            if confidence >= 0:
                confidences.append(confidence)
        except (IndexError, TypeError, ValueError):
            continue

    text = "\n".join(" ".join(words) for words in lines.values()).strip()
    confidence = sum(confidences) / len(confidences) if confidences else None
    return text, confidence, len(confidences)


def _extract_image(file_path: str):
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image file not found: {file_path}")

    pages = []
    confidence_total = 0.0
    confidence_words = 0
    with Image.open(path) as image:
        frame_count = getattr(image, "n_frames", 1)
        if frame_count > 30:
            raise ValueError("TIFF files may contain no more than 30 pages.")
        for frame_number in range(frame_count):
            image.seek(frame_number)
            text, confidence, word_count = _image_to_text_and_confidence(image)
            if frame_count > 1:
                pages.append(f"--- Page {frame_number + 1} ---\n{text}")
            else:
                pages.append(text)
            if confidence is not None:
                confidence_total += confidence * word_count
                confidence_words += word_count

    confidence = confidence_total / confidence_words if confidence_words else None
    return "\n\n".join(pages).strip(), confidence


def _extract_pdf(file_path: str):
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    extracted_pages = []
    confidence_total = 0.0
    confidence_words = 0
    with pymupdf.open(path) as pdf:
        if len(pdf) > 30:
            raise ValueError("PDFs may contain no more than 30 pages.")
        for page_number, page in enumerate(pdf, start=1):
            text = page.get_text("text").strip()
            if len(text) < 20:
                pixmap = page.get_pixmap(dpi=200, alpha=False)
                with Image.open(io.BytesIO(pixmap.tobytes("png"))) as image:
                    text, confidence, word_count = _image_to_text_and_confidence(image)
                    if confidence is not None:
                        confidence_total += confidence * word_count
                        confidence_words += word_count
            extracted_pages.append(f"--- Page {page_number} ---\n{text}")

    confidence = confidence_total / confidence_words if confidence_words else None
    return "\n\n".join(extracted_pages).strip(), confidence


def extract_text_with_confidence(file_path: str, document_type: str):
    """Return (text, confidence percent); direct-text PDFs report None."""
    document_type = document_type.upper()
    if document_type == "PDF":
        return _extract_pdf(file_path)
    if document_type in {"JPEG", "JPG", "PNG", "TIFF", "TIF"}:
        return _extract_image(file_path)
    raise ValueError(f"Unsupported document type: {document_type}")


def extract_text_from_image(file_path: str) -> str:
    return _extract_image(file_path)[0]


def extract_text_from_pdf(file_path: str) -> str:
    return _extract_pdf(file_path)[0]


def extract_text_from_document(file_path: str, document_type: str) -> str:
    return extract_text_with_confidence(file_path, document_type)[0]
