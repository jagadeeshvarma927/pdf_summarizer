import fitz  # PyMuPDF
# file.file.seek(0)


def extract_text_from_pdf(file):
    """
    Extract full text from uploaded PDF file
    """
    pdf_bytes = file.file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    full_text = ""

    for page in doc:
        full_text += page.get_text()

    doc.close()
    return full_text
