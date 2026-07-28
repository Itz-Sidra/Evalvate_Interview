import io
import re
import unicodedata

import docx
import pdfplumber


def extract_text_from_pdf(file_bytes: bytes) -> str:
    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            # layout=True preserves spatial arrangement for multi-column resumes
            extracted = page.extract_text(layout=True)
            if not extracted:
                extracted = page.extract_text() or ""
            text_parts.append(extracted)
            
            # Extract hyperlinks
            for link in page.hyperlinks:
                uri = link.get("uri")
                if uri:
                    text_parts.append(f"[Link: {uri}]")
    return "\n".join(text_parts)


def extract_text_from_docx(file_bytes: bytes) -> str:
    document = docx.Document(io.BytesIO(file_bytes))
    lines = [paragraph.text for paragraph in document.paragraphs]
    
    # Extract hyperlinks from relationships
    for rel in document.part.rels.values():
        if "hyperlink" in rel.reltype:
            lines.append(f"[Link: {rel.target_ref}]")
            
    return "\n".join(lines)


def clean_extracted_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.encode("utf-8", errors="ignore").decode("utf-8")
    # Do not collapse spaces; we must preserve newlines and spatial gutters for downstream parsing
    return normalized.strip()
