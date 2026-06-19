import re

SKILLS_HEADERS     = {"skills", "technical skills", "core competencies", "competencies", "technologies"}
EXPERIENCE_HEADERS = {"experience", "work experience", "professional experience", "employment history", "career history"}
EDUCATION_HEADERS  = {"education", "academic background", "qualifications", "academic qualifications"}
SUMMARY_HEADERS    = {"summary", "profile", "objective", "about me", "professional summary", "career objective"}


def _section_header(line: str) -> str | None:
    """Return normalised header name if the line looks like a CV section header."""
    clean = line.strip().rstrip(":").lower()
    for group in (SKILLS_HEADERS, EXPERIENCE_HEADERS, EDUCATION_HEADERS, SUMMARY_HEADERS):
        if clean in group:
            return clean
    return None


def parse_cv_sections(full_text: str) -> dict:
    """
    Split raw CV text into named sections.

    Returns a dict with keys: skills_text, experience_text, education_text,
    summary_text, and full_text (the original input).

    Sections are detected by common header keywords. Falls back to the full
    text for any section that could not be found.
    """
    lines = full_text.splitlines()

    sections: dict[str, list[str]] = {
        "skills":     [],
        "experience": [],
        "education":  [],
        "summary":    [],
    }
    current: str | None = None
    bucket_map = {
        **{h: "skills"     for h in SKILLS_HEADERS},
        **{h: "experience" for h in EXPERIENCE_HEADERS},
        **{h: "education"  for h in EDUCATION_HEADERS},
        **{h: "summary"    for h in SUMMARY_HEADERS},
    }

    for line in lines:
        header = _section_header(line)
        if header and header in bucket_map:
            current = bucket_map[header]
            continue
        if current:
            sections[current].append(line)

    def text_or_full(key: str) -> str:
        extracted = "\n".join(sections[key]).strip()
        return extracted if extracted else full_text[:2000]

    return {
        "skills_text":     text_or_full("skills"),
        "experience_text": text_or_full("experience"),
        "education_text":  text_or_full("education"),
        "summary_text":    text_or_full("summary"),
        "full_text":       full_text,
    }


def extract_skills_from_text(text: str) -> list[str]:
    """
    Best-effort skill extraction from free-form text.
    Looks for comma/bullet/pipe-separated tokens of 1-4 words.
    """
    # Replace bullets and pipes with commas
    normalised = re.sub(r"[•·|▪▸–]", ",", text)
    # Split on commas and newlines
    tokens = re.split(r"[,\n]+", normalised)
    skills = []
    for tok in tokens:
        tok = tok.strip().strip(".")
        # Accept 1–4 words, not too long
        if tok and 1 <= len(tok.split()) <= 4 and len(tok) <= 40:
            skills.append(tok)
    return skills[:30]  # cap at 30 to avoid noise
