import re


def extract_section(text: str, keywords: list) -> str:
    """
    Search CV text for a section heading and extract content under it.
    Returns empty string if section not found.
    """
    text_lower = text.lower()

    for keyword in keywords:
        # Find the keyword position in text
        pos = text_lower.find(keyword.lower())
        if pos != -1:
            # Extract text from that position onwards
            section_text = text[pos:]

            # Find where the next section starts (look for next heading)
            # Headings are usually short lines in ALL CAPS or followed by newline
            lines = section_text.split('\n')
            result_lines = []

            # Skip the heading line itself
            for line in lines[1:]:
                # Stop if we hit another section heading
                if any(
                    kw.lower() in line.lower()
                    for kw in [
                        "experience", "education", "skills", "projects",
                        "certifications", "references", "summary", "objective",
                        "employment", "work history", "qualifications"
                    ]
                ) and len(line.strip()) < 50:
                    break
                result_lines.append(line)

            extracted = ' '.join(result_lines).strip()
            if len(extracted) > 30:
                return extracted

    return ""


def parse_cv_sections(
    raw_text: str,
    fallback_skills: list = None,
    fallback_experience: str = ""
) -> dict:
    """
    Split raw CV text into 3 sections for embedding.

    Args:
        raw_text: Full CV text extracted by File Service
        fallback_skills: Skills user typed during WhatsApp onboarding
        fallback_experience: Experience level from onboarding (junior/mid/senior)

    Returns:
        Dictionary with skills, experience, summary sections
    """

    # --- Section 1: Skills ---
    skills_text = extract_section(raw_text, [
        "skills", "technical skills", "core competencies",
        "technologies", "tools", "expertise", "competencies"
    ])

    # Fallback to onboarding skills if CV has no skills section
    if not skills_text and fallback_skills:
        skills_text = ', '.join(fallback_skills)

    # Last resort fallback
    if not skills_text:
        skills_text = "general skills"

    # --- Section 2: Experience ---
    experience_text = extract_section(raw_text, [
        "experience", "work experience", "work history",
        "employment", "employment history", "professional experience"
    ])

    # Fallback to onboarding experience level
    if not experience_text and fallback_experience:
        experience_text = f"{fallback_experience} level professional"

    # Last resort fallback
    if not experience_text:
        experience_text = "professional with relevant experience"

    # --- Section 3: Summary ---
    # Always use first 2000 characters — no parsing needed
    summary_text = raw_text[:2000].strip()

    return {
        "skills": skills_text,
        "experience": experience_text,
        "summary": summary_text
    }