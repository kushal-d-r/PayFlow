
from invoices.services.ocr import extract_text_with_confidence
from invoices.services.extraction import extract_invoice_data
from invoices.services.validation import validate_invoice_data
from invoices.services.duplicate import check_duplicate_invoice
from vendors.models import Vendor


def process_invoice_document(document):
    """
    Process an uploaded invoice document.

    Pipeline:
    OCR -> Extraction -> Validation -> Vendor matching
    -> Duplicate detection
    """

    # 1. Extract raw text using OCR
    extracted_text, ocr_confidence = extract_text_with_confidence(
        document.file.path,
        document.document_type,
    )

    if not extracted_text.strip():
        raise ValueError(
            "No readable text found in the uploaded document."
        )

    # 2. Extract structured invoice fields
    extracted_data = extract_invoice_data(extracted_text)
    extracted_data["ocr_confidence"] = (
        round(ocr_confidence, 1) if ocr_confidence is not None else None
    )
    extracted_data["ocr_confidence_label"] = (
        "High" if ocr_confidence is not None and ocr_confidence >= 85
        else "Review" if ocr_confidence is not None and ocr_confidence >= 65
        else "Low" if ocr_confidence is not None
        else "Not measured (text PDF)"
    )

    # 3. Validate extracted fields
    validation_result = validate_invoice_data(extracted_data)
    if ocr_confidence is not None and ocr_confidence < 65:
        validation_result["warnings"].append(
            "OCR confidence is low. Verify extracted fields against the document."
        )

    # 4. Match vendor using GSTIN
    gstin = extracted_data.get("gstin")
    matched_vendor = None

    if gstin:
        matched_vendor = Vendor.objects.filter(
            gstin__iexact=gstin.strip()
        ).first()

    vendor_result = {
        "matched": matched_vendor is not None,
        "vendor_id": matched_vendor.id if matched_vendor else None,
        "vendor_name": (
            matched_vendor.legal_name
            if matched_vendor else None
        ),
        "message": (
            "Vendor matched successfully."
            if matched_vendor
            else "Vendor not found. Manual review required."
        ),
    }

    # 5. Check duplicate invoice
    invoice_number = extracted_data.get("invoice_number")

    if matched_vendor and invoice_number:
        duplicate_result = check_duplicate_invoice(
            matched_vendor,
            invoice_number,
        )
    else:
        duplicate_result = {
            "is_duplicate": False,
            "message": (
                "Duplicate check skipped because vendor "
                "or invoice number is missing."
            ),
        }

    # 6. Combine processing results
    extracted_data["validation"] = validation_result
    extracted_data["vendor_match"] = vendor_result
    extracted_data["duplicate_check"] = duplicate_result

    return {
        "extracted_text": extracted_text,
        "extracted_data": extracted_data,
    }
