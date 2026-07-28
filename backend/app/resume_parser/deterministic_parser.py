import re
from typing import Any

def extract_email(text: str) -> str | None:
    match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    return match.group(0) if match else None

def extract_phone(text: str) -> str | None:
    match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
    return match.group(0) if match else None

def extract_skills(text: str) -> list[str]:
    SKILL_DICTIONARY = {
        "python", "java", "c++", "javascript", "typescript", "react", "angular", "vue",
        "sql", "nosql", "aws", "azure", "gcp", "docker", "kubernetes", "machine learning",
        "artificial intelligence", "data science", "nlp", "computer vision", "git", "linux",
        "agile", "scrum", "project management", "html", "css", "django", "flask", "fastapi"
    }
    found_skills = set()
    text_lower = text.lower()
    for skill in SKILL_DICTIONARY:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_lower):
            found_skills.add(skill.title())
    return list(found_skills)

def extract_dates(text: str) -> list[str]:
    # Extract common date ranges e.g. Jan 2020 - Present, 2018 - 2020
    pattern = r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}|\d{4})\s*[-–]\s*(Present|Current|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}|\d{4})"
    matches = re.findall(pattern, text, re.IGNORECASE)
    return [f"{m[0]} - {m[1]}" for m in matches]

def extract_sections(text: str) -> dict[str, str]:
    sections = {"summary": "", "experience": "", "education": "", "skills": ""}
    lines = text.split("\n")
    current_section = None
    
    for line in lines:
        line_clean = line.strip().lower()
        if re.match(r"^(experience|work history|employment)\b", line_clean):
            current_section = "experience"
            continue
        elif re.match(r"^(education|academic background)\b", line_clean):
            current_section = "education"
            continue
        elif re.match(r"^(skills|core competencies)\b", line_clean):
            current_section = "skills"
            continue
        elif re.match(r"^(summary|profile|objective)\b", line_clean):
            current_section = "summary"
            continue
        
        if current_section:
            sections[current_section] += line + "\n"
            
    return sections

def parse_resume_deterministic(text: str) -> dict[str, Any]:
    email = extract_email(text)
    phone = extract_phone(text)
    skills = extract_skills(text)
    
    sections = extract_sections(text)
    
    experience_list = []
    if sections["experience"]:
        # Naive extraction using dates as block delimiters
        dates = extract_dates(sections["experience"])
        # If we have dates, assume they mark experience items
        if dates:
            experience_list = [{"company": None, "role": None, "duration": d, "description": sections["experience"][:200]} for d in dates]

    return {
        "email": email,
        "phone": phone,
        "skills": skills if skills else None,
        "name": None, # Name requires NER, fallback to LLM
        "summary": sections["summary"].strip() if sections["summary"].strip() else None,
        "education": None, # Complex to format perfectly, fallback to LLM
        "experience": experience_list if experience_list else None,
    }

def merge_parsed_results(deterministic: dict, llm: dict) -> dict:
    merged = {}
    for key in ["name", "email", "phone", "summary", "skills", "education", "experience"]:
        d_val = deterministic.get(key)
        l_val = llm.get(key)
        
        if d_val is not None and (not isinstance(d_val, list) or len(d_val) > 0):
            if key == "skills" and l_val:
                merged[key] = list(set(d_val + l_val))
            elif key == "experience" and l_val:
                # Deterministic experience extraction is naive, prefer LLM if it found experience
                # but enrich with deterministic dates if missing
                merged[key] = l_val
            else:
                merged[key] = d_val
        else:
            merged[key] = l_val
    return merged
