import fitz  # PyMuPDF


def extract_pdf_text(pdf_bytes: bytes) -> tuple[str, int]:
    """Extract selectable text from every page of a PDF.

    Returns (text, page_count). Text is empty for scanned/image-only PDFs.
    """
    with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
        page_text = [page.get_text("text") for page in pdf]
        page_count = len(pdf)
    return "\n\n".join(page_text).strip(), page_count
