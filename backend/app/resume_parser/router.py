import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.middlewares.auth_context import get_authenticated_user_id
from app.resume_parser.repository import (
    delete_resumes_for_user,
    get_latest_resume_for_user,
    serialize_resume_document,
)
from app.resume_parser.schemas import CurrentResumeResponse, DeleteResumeResponse, UploadResumeResponse, JDUploadResponse, MatchResult, ParsedJD
from app.resume_parser.service import process_resume_upload
from app.resume_parser.jd_engine import parse_jd_with_llm, extract_text_from_url
from app.resume_parser.matcher import match_resume_to_jd
from app.resume_parser.intelligence import rewrite_resume_bullet, generate_interview_questions
from pydantic import BaseModel

class URLRequest(BaseModel):
    url: str

class JDTextRequest(BaseModel):
    text: str

class RewriteRequest(BaseModel):
    text: str

logger = logging.getLogger(__name__)

router = APIRouter(tags=["resume-parser"])


@router.get("/resume", response_model=CurrentResumeResponse)
async def get_current_resume(
    user_id: str = Depends(get_authenticated_user_id),
    db: AsyncSession = Depends(get_db),
):
    doc = await get_latest_resume_for_user(db=db, user_id=user_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No parsed resume found for this user",
        )

    return serialize_resume_document(doc)


@router.delete("/resume", response_model=DeleteResumeResponse)
async def delete_current_resume(
    user_id: str = Depends(get_authenticated_user_id),
    db: AsyncSession = Depends(get_db),
):
    deleted_count = await delete_resumes_for_user(db=db, user_id=user_id)
    if deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No parsed resume found for this user",
        )

    return {
        "message": "Resume data deleted successfully",
        "deleted_count": deleted_count,
    }


@router.post("/upload-resume", response_model=UploadResumeResponse)
async def upload_resume(
    user_id: str = Depends(get_authenticated_user_id),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    logger.info("Processing resume upload: filename=%s user_id=%s", file.filename, user_id)
    try:
        return await process_resume_upload(file=file, db=db, user_id=user_id)
    finally:
        await file.close()

@router.post("/upload-jd", response_model=JDUploadResponse)
async def upload_jd_file(
    file: UploadFile = File(...),
):
    # Quick implementation for JD upload via file
    file_bytes = await file.read()
    from app.resume_parser.extractor import extract_text_from_docx, extract_text_from_pdf
    if file.filename and file.filename.lower().endswith(".pdf"):
        text = extract_text_from_pdf(file_bytes)
    else:
        text = extract_text_from_docx(file_bytes)
    
    parsed = await parse_jd_with_llm(text)
    return {"jd_id": "temp_jd_id", "parsed_jd": parsed}

@router.post("/upload-jd-url", response_model=JDUploadResponse)
async def upload_jd_url(req: URLRequest):
    text = extract_text_from_url(req.url)
    parsed = await parse_jd_with_llm(text)
    return {"jd_id": "temp_jd_id", "parsed_jd": parsed}

@router.post("/upload-jd-text", response_model=JDUploadResponse)
async def upload_jd_text(req: JDTextRequest):
    parsed = await parse_jd_with_llm(req.text)
    return {"jd_id": "temp_jd_id", "parsed_jd": parsed}

@router.post("/match-resume")
async def match_resume(resume_id: str, jd_id: str, db: AsyncSession = Depends(get_db)):
    # In a real system, we fetch parsed_resume and parsed_jd from DB.
    # For now, we mock the retrieval since we don't have JD storage implemented fully.
    return {"message": "Match endpoint ready"}

@router.post("/rewrite-bullet")
async def rewrite_bullet(req: RewriteRequest):
    rewritten = await rewrite_resume_bullet(req.text)
    return {"rewritten_text": rewritten}

@router.get("/interview-intelligence/{resume_id}")
async def get_interview_intelligence(resume_id: str, db: AsyncSession = Depends(get_db)):
    # We would fetch resume from DB and run intelligence
    # doc = await get_resume_by_id(db, resume_id)
    # iq = await generate_interview_questions(doc.parsed_resume)
    return {"message": "Interview intelligence ready"}