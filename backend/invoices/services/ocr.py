import io
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image
from django.conf import settings


# Configure the Tesseract OCR executable.
pytesseract.pytesseract.tesseract_cmd = getattr(
    settings,
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
)


def extract_text_from_image(file_path: str) -> str:
    """
    Extract English text from a JPG, JPEG, or PNG image.
    """
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Image file not found: {file_path}"
        )

    with Image.open(path) as image:
        image = image.convert("RGB")
        text = pytesseract.image_to_string(
            image,
            lang="eng",
        )

    return text.strip()


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from every page of a PDF.

    Digitally generated PDFs use direct text extraction.
    Scanned pages use Tesseract OCR.
    """
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"PDF file not found: {file_path}"
        )

    extracted_pages = []

    with pymupdf.open(path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            text = page.get_text("text").strip()

            # Use OCR when the PDF page contains little or no text.
            if len(text) < 20:
                pixmap = page.get_pixmap(
                    dpi=200,
                    alpha=False,
                )

                image_bytes = pixmap.tobytes("png")

                with Image.open(
                    io.BytesIO(image_bytes)
                ) as image:
                    image = image.convert("RGB")
                    text = pytesseract.image_to_string(
                        image,
                        lang="eng",
                    ).strip()

            extracted_pages.append(
                f"--- Page {page_number} ---\n{text}"
            )

    return "\n\n".join(extracted_pages).strip()


def extract_text_from_document(
    file_path: str,
    document_type: str,
) -> str:
    """
    Select the appropriate extraction method for the document.
    """
    document_type = document_type.upper()

    if document_type == "PDF":
        return extract_text_from_pdf(file_path)

    if document_type in {"JPEG", "JPG", "PNG"}:
        return extract_text_from_image(file_path)

    raise ValueError(
        f"Unsupported document type: {document_type}"
    )