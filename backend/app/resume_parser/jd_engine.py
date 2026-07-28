import json
import logging
import requests
from bs4 import BeautifulSoup
from app.resume_parser.llm_client import _call_openrouter_api, _strip_code_fences

logger = logging.getLogger(__name__)

JD_SYSTEM_PROMPT = (
    "You are an expert technical recruiter analyzing a job description. "
    "Extract the title, requirements, skills, and responsibilities. "
    "Return clean JSON only with no markdown and no extra text."
)

def _build_jd_user_prompt(jd_text: str) -> str:
    return (
        "Extract job data into this exact JSON schema:\n"
        "{\n"
        '  "title": "string | null",\n'
        '  "requirements": ["string"],\n'
        '  "skills": ["string"],\n'
        '  "responsibilities": ["string"]\n'
        "}\n\n"
        f"Job Description Text:\n{jd_text}"
    )

def extract_text_from_url(url: str) -> str:
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        logger.error(f"Failed to extract from URL {url}: {e}")
        return ""

async def parse_jd_with_llm(jd_text: str) -> dict:
    raw_output = await _call_openrouter_api(
        system_prompt=JD_SYSTEM_PROMPT,
        user_prompt=_build_jd_user_prompt(jd_text)
    )
    parsed = json.loads(_strip_code_fences(raw_output))
    return {
        "title": parsed.get("title"),
        "requirements": parsed.get("requirements") or [],
        "skills": parsed.get("skills") or [],
        "responsibilities": parsed.get("responsibilities") or []
    }
