import fitz  # PyMuPDF


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from PDF bytes using PyMuPDF."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def parse_cv_sections(raw_text: str) -> dict:
    """
    Basic structural parse of CV text.
    Returns metadata useful for display. Full AI-powered parsing added in Phase 2.
    """
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    return {
        "word_count": len(raw_text.split()),
        "line_count": len(lines),
        "has_contact_email": any("@" in line for line in lines),
        "estimated_years_experience": None,  # populated by Claude in Phase 2
    }
