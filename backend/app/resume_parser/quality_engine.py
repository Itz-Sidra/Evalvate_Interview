import re
from typing import Any

ACTION_VERBS = {"developed", "managed", "created", "led", "designed", "implemented", "optimized", "increased", "decreased", "spearheaded", "orchestrated", "engineered"}

def check_action_verbs(text: str) -> list[str]:
    text_lower = text.lower()
    return [v for v in ACTION_VERBS if f" {v} " in text_lower or text_lower.startswith(f"{v} ")]

def check_metrics(text: str) -> bool:
    if "%" in text or "$" in text:
        return True
    if re.search(r"\b\d{2,}\b", text):
        return True
    return False

def check_grammar(text: str) -> list[str]:
    issues = []
    if "  " in text.replace("   ", " "):
        issues.append("Double spaces found.")
    if " ," in text or " ." in text:
        issues.append("Punctuation spacing errors (space before comma or period).")
    return issues

def check_bullet_quality(text: str) -> list[dict]:
    lines = text.split("\n")
    issues = []
    for line in lines:
        line_clean = line.strip()
        if line_clean.startswith("-") or line_clean.startswith("•"):
            bullet = line_clean[1:].strip()
            if len(bullet.split()) < 5:
                issues.append({"type": "too_short", "bullet": bullet})
            if not check_metrics(bullet):
                issues.append({"type": "no_metrics", "bullet": bullet})
    return issues

def run_quality_engine(parsed_resume: dict, raw_text: str) -> dict[str, Any]:
    findings = []
    deductions = 0
    
    # Grammar
    grammar_issues = check_grammar(raw_text)
    for issue in grammar_issues:
        findings.append(f"[Grammar] {issue}")
        deductions += 2

    # Action verbs
    verbs = check_action_verbs(raw_text)
    if len(verbs) < 5:
        findings.append(f"[Action Verbs] Found only {len(verbs)} strong action verbs. Use more impact verbs.")
        deductions += 5
        
    # Metrics
    if not check_metrics(raw_text):
        findings.append("[Metrics] No quantifiable metrics found (%, $, numbers). Add metrics to prove impact.")
        deductions += 10
        
    # Bullet quality in Experience
    experience = parsed_resume.get("experience") or []
    if not experience:
        findings.append("[Experience] No professional experience section found.")
        deductions += 15
    else:
        for exp in experience:
            desc = exp.get("description", "")
            if desc:
                issues = check_bullet_quality(desc)
                no_metrics_count = sum(1 for i in issues if i["type"] == "no_metrics")
                if no_metrics_count > 0:
                    findings.append(f"[Bullets] Experience at '{exp.get('company', 'Unknown')}' has {no_metrics_count} bullet(s) without metrics.")
                    deductions += (no_metrics_count * 2)

    # Education
    if not parsed_resume.get("education"):
        findings.append("[Education] No education section found.")
        deductions += 5
        
    # Skills
    if not parsed_resume.get("skills"):
        findings.append("[Skills] No recognizable skills extracted.")
        deductions += 10

    # ATS Readability
    if len(raw_text.split()) < 100:
        findings.append("[ATS Readability] Resume is too short (< 100 words), might be rejected by ATS.")
        deductions += 10

    return {
        "overall_score": max(0, 100 - deductions),
        "score_breakdown": {
            "keyword_alignment": 100 if parsed_resume.get("skills") else 50,
            "formatting": 100 - (len(grammar_issues) * 5),
            "readability": 100 if len(raw_text.split()) >= 100 else 50,
            "section_completeness": max(0, 100 - (15 if not experience else 0) - (5 if not parsed_resume.get("education") else 0)),
        },
        "deterministic_findings": findings
    }
