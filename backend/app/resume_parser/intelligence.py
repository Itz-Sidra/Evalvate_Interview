import json
from app.resume_parser.llm_client import _call_openrouter_api, _strip_code_fences

REWRITE_SYSTEM_PROMPT = (
    "You are an expert resume writer. "
    "Rewrite the given resume bullet or section to improve clarity, impact, and action verbs. "
    "CRITICAL RULE: Never invent information, metrics, or experiences that are not present in the original text. "
    "Return only the rewritten text, nothing else."
)

INTERVIEW_SYSTEM_PROMPT = (
    "You are an expert technical interviewer analyzing a candidate's resume claims. "
    "Generate 3 deep technical interview questions based strictly on their claimed skills and experience. "
    "Return clean JSON only with no markdown and no extra text."
)

async def rewrite_resume_bullet(text: str) -> str:
    raw_output = await _call_openrouter_api(
        system_prompt=REWRITE_SYSTEM_PROMPT,
        user_prompt=f"Rewrite this to be more impactful while maintaining absolute factual accuracy:\n{text}"
    )
    return raw_output.strip()

async def generate_interview_questions(parsed_resume: dict) -> dict:
    prompt = (
        "Based on the following candidate profile, generate 3 interview questions that probe their claims.\n"
        "Return this exact JSON schema:\n"
        "{\n"
        '  "questions": ["string"],\n'
        '  "skill_confidence": {"skill_name": "High/Medium/Low"},\n'
        '  "trust_score": "integer 0-100"\n'
        "}\n\n"
        f"Resume:\n{json.dumps(parsed_resume, indent=2)}"
    )
    raw_output = await _call_openrouter_api(
        system_prompt=INTERVIEW_SYSTEM_PROMPT,
        user_prompt=prompt
    )
    try:
        parsed = json.loads(_strip_code_fences(raw_output))
        return {
            "questions": parsed.get("questions", []),
            "skill_confidence": parsed.get("skill_confidence", {}),
            "trust_score": parsed.get("trust_score", 50)
        }
    except Exception:
        return {
            "questions": [],
            "skill_confidence": {},
            "trust_score": 0
        }
