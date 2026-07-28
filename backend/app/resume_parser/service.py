import asyncio
import logging
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.resume_parser.extractor import clean_extracted_text, extract_text_from_docx, extract_text_from_pdf
from app.resume_parser.llm_client import analyze_resume_ats_with_llm, parse_resume_with_llm
from app.resume_parser.repository import build_resume_document
from app.resume_parser.validator import validate_file_metadata, validate_resume_content
from app.resume_parser.deterministic_parser import parse_resume_deterministic, merge_parsed_results

logger = logging.getLogger(__name__)



async def _extract_resume_text(suffix: str, file_bytes: bytes) -> str:
    try:
        if suffix == ".pdf":
            raw_text = await asyncio.to_thread(extract_text_from_pdf, file_bytes)
        else:
            raw_text = await asyncio.to_thread(extract_text_from_docx, file_bytes)
    except Exception as exc:
        logger.exception("Failed to extract resume text")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to extract text from resume",
        ) from exc

    cleaned_text = clean_extracted_text(raw_text)
    if not cleaned_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Extracted resume text is empty",
        )

    return cleaned_text


async def _store_parsed_resume(
    *,
    db: AsyncSession,
    parsed_resume: dict,
    ats_analysis: dict | None,
    raw_text: str,
    file: UploadFile,
    user_id: str | None,
) -> tuple[str, object]:
    doc = build_resume_document(
        parsed_resume=parsed_resume,
        ats_analysis=ats_analysis,
        raw_text=raw_text,
        filename=file.filename or "unknown",
        content_type=file.content_type,
        user_id=user_id,
    )
    db.add(doc)
    await db.flush()
    return str(doc.id), doc.created_at


async def process_resume_upload(
    *,
    file: UploadFile,
    db: AsyncSession,
    user_id: str | None,
) -> dict:
    # Step 1: Read bytes once from the upload stream.
    file_bytes = await file.read()

    # Step 2: Validate file extension, content type, and file size.
    suffix = validate_file_metadata(file.filename or "", file.content_type or "", file_bytes)

    # Step 3: Extract and clean text using format-specific parser.
    resume_text = await _extract_resume_text(suffix, file_bytes)

    # Step 3.5: Validate resume content
    validate_resume_content(resume_text)

    # Step 4: Deterministic parsing
    deterministic_resume = parse_resume_deterministic(resume_text)

    # Step 4.5: Send cleaned text to LLM to fill missing ambiguous fields
    llm_resume = await parse_resume_with_llm(resume_text)
    
    # Merge outputs
    parsed_resume = merge_parsed_results(deterministic_resume, llm_resume)

    # Step 4.75: Deterministic Quality Engine (Phase 4 & 7)
    from app.resume_parser.quality_engine import run_quality_engine
    quality_results = run_quality_engine(parsed_resume, resume_text)

    # Step 5: Recruiter Simulation (Phase 8)
    ats_analysis: dict | None
    try:
        recruiter_insights = await analyze_resume_ats_with_llm(resume_text, parsed_resume)
        
        # Merge quality_engine deterministic scores with recruiter LLM insights
        ats_analysis = {
            "overall_score": quality_results["overall_score"],
            "score_breakdown": quality_results["score_breakdown"],
            "strengths": recruiter_insights.get("strengths", []),
            "wording_tips": recruiter_insights.get("wording_tips", []),
            "formatting_tips": recruiter_insights.get("formatting_tips", []),
            "useful_insights": quality_results["deterministic_findings"] + recruiter_insights.get("useful_insights", [])
        }
    except HTTPException:
        logger.exception("Failed to generate Recruiter insights. Falling back to deterministic only.")
        ats_analysis = {
            "overall_score": quality_results["overall_score"],
            "score_breakdown": quality_results["score_breakdown"],
            "strengths": [],
            "wording_tips": [],
            "formatting_tips": [],
            "useful_insights": quality_results["deterministic_findings"] + [
                "Resume parsed successfully, but recruiter insights are temporarily unavailable."
            ],
        }

    # Step 6: Store parsed output and ATS insights in PostgreSQL.
    resume_id, created_at = await _store_parsed_resume(
        db=db,
        parsed_resume=parsed_resume,
        ats_analysis=ats_analysis,
        raw_text=resume_text,
        file=file,
        user_id=user_id,
    )

    return {
        "resume_id": resume_id,
        "parsed_resume": parsed_resume,
        "ats_analysis": ats_analysis,
        "created_at": created_at,
    }