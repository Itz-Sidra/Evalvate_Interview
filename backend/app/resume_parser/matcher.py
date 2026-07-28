def match_resume_to_jd(parsed_resume: dict, parsed_jd: dict) -> dict:
    resume_skills = set(s.lower() for s in (parsed_resume.get("skills") or []))
    jd_skills = set(s.lower() for s in (parsed_jd.get("skills") or []))
    
    matched_skills = list(resume_skills.intersection(jd_skills))
    missing_skills = list(jd_skills - resume_skills)
    
    skill_score = (len(matched_skills) / len(jd_skills) * 100) if jd_skills else 100
    
    evidence = []
    if matched_skills:
        evidence.append(f"Matched {len(matched_skills)} skills: {', '.join(matched_skills)}")
    if missing_skills:
        evidence.append(f"Missing {len(missing_skills)} skills: {', '.join(missing_skills)}")
        
    return {
        "matched_skills": [s.title() for s in matched_skills],
        "missing_skills": [s.title() for s in missing_skills],
        "match_score": int(skill_score),
        "evidence": evidence
    }
