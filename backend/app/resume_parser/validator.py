import logging
from pathlib import Path
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",
}

# Keywords typical in resumes
RESUME_KEYWORDS = {
    "experience", "education", "skills", "work history",
    "employment", "summary", "objective", "projects",
    "certifications", "languages", "professional background"
}

# Negative heuristics
REJECT_PATTERNS = [
    "certificate of completion",
    "certificate of achievement",
    "proudly presented to",
    "course syllabus",
    "homework assignment",
    "table of contents",
    "semester",
]

def validate_file_metadata(filename: str, content_type: str, file_bytes: bytes) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF and DOCX are supported",
        )

    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content type. Only PDF and DOCX are supported",
        )

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File is too large. Maximum size is 5MB",
        )

    return suffix


def validate_resume_content(text: str) -> None:
    if not text or len(text.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Extracted document is empty or corrupted",
        )

    text_lower = text.lower()
    
    # Reject non-resumes (certificates, assignments, reports)
    for pattern in REJECT_PATTERNS:
        if pattern in text_lower:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Document rejected: appears to be a non-resume (detected '{pattern}')",
            )
            
    # Require at least some standard resume keywords to prove it's a resume
    matches = sum(1 for kw in RESUME_KEYWORDS if kw in text_lower)
    if matches < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document rejected: does not appear to be a valid resume",
        )
