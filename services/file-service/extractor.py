import io
import pdfplumber
import pytesseract
from PIL import Image
from docx import Document


def extract_from_pdf(file_bytes: bytes) -> str:
    """
    Extract text from PDF.
    First tries pdfplumber (digital PDFs).
    Falls back to pytesseract OCR if no text found (scanned PDFs).
    """
    text = ""

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    # If pdfplumber got nothing the PDF is likely scanned — use OCR
    if not text.strip():
        text = _ocr_pdf(file_bytes)

    return text.strip()


def _ocr_pdf(file_bytes: bytes) -> str:
    """Convert each PDF page to image and run Tesseract OCR."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = ""
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text += pytesseract.image_to_string(img) + "\n"
        return text
    except ImportError:
        # PyMuPDF not installed — skip OCR fallback
        return ""
    except Exception as e:
        print(f"[WARN] OCR failed: {e}")
        return ""


def extract_from_docx(file_bytes: bytes) -> str:
    """Extract text from Word .docx file."""
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def extract_text(file_bytes: bytes, mime_type: str) -> tuple[str, str]:
    """
    Route to correct extractor based on MIME type.
    Returns (extracted_text, file_type).
    """
    pdf_types  = {"application/pdf"}
    docx_types = {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    }

    if mime_type in pdf_types:
        return extract_from_pdf(file_bytes), "pdf"

    if mime_type in docx_types:
        return extract_from_docx(file_bytes), "docx"

    # Unknown type — try PDF extraction as best guess
    try:
        return extract_from_pdf(file_bytes), "pdf"
    except Exception:
        return "", "unknown"
