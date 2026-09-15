import fitz
import docx
import base64
import anthropic
import io
import os 
from dotenv import load_dotenv

load_dotenv()

def get_api_key():
    try:
        import streamlit as st
        return st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    except:
        return os.getenv("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=get_api_key())


def extract_from_pdf(file_bytes):
    """Extracts text from PDF byte using PyMuPDF."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text())
    return "\n".join(pages)

def extract_from_docx(file_bytes):
    """Extract text from Word document bytes."""
    doc = docx.Document(io.BytesIO(file_bytes))
    paragraphs = []
    for para in doc.paragraphs:
        if para.text.strip():    # skip empty paragraphs
            paragraphs.append(para.text)
    return "\n".join(paragraphs)

def extract_from_image(file_bytes, media_type):
    """Send image to Claude Vision for text extraction."""
    try:
        b64_image = base64.b64encode(file_bytes).decode("utf-8")

        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64_image
                        }
                    },
                    {
                        "type": "text",
                        "text": """Extract ALL text from this legal document image.
                        Preserve the structure - headings, numberes clauses,
                        paragraphs - as accurately as possible.
                        If the image is too blurry or unclear to read reliably, respond with:
                        ERROR: Image too unclear to extract text.
                        Please upload a clearer photo."""
                    }
                ]
            }]
        )
        result = message.content[0].text
        return result
    except Exception as e:
        return f"ERROR: Could not process image - {str(e)}"


def extract_text(uploaded_file):
    """Main extraction function. Takes a Streamlit uploaded file object.
    Returns extracted text as a string."""
    file_bytes = uploaded_file.read()
    filename = uploaded_file.name.lower()

    if filename.endswith(".pdf"):
        return extract_from_pdf(file_bytes), "pdf"

    elif filename.endswith(".docx") or filename.endswith(".doc"):
        return extract_from_docx(file_bytes), "docx"

    elif filename.endswith((".png", ".jpg", ".jpeg", ".webp")):   # determine media type for Claude
        if filename.endswith(".png"):
            media_type = "image/png"
        elif filename.endswith(".webp"):
            media_type = "image/webp"
        else:
            media_type = "image/jpeg"
        return extract_from_image(file_bytes, media_type), "image"

    else:
        return "ERROR: Unsupported file type.", "unknown"



















