import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from cv_parser import parse_cv_sections

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


EXTRACTION_PROMPT = """
You are an expert HR analyst. Read the entire CV below carefully.

Return ONLY a valid JSON object with exactly these fields:

{{
    "role_title": "The most accurate job title for this person based on their experience. Use standard industry titles like: Software Engineer, Backend Developer, Frontend Developer, Full Stack Developer, Data Scientist, Machine Learning Engineer, DevOps Engineer, Mobile Developer. Pick the single best fitting title.",
    "experience_years": "Number of years of professional experience as a single integer. If unclear write 0.",
    "experience_level": "One word only: junior or mid or senior or lead. Base this on years of experience and responsibilities described.",
    "skills": "Comma separated list of ONLY technical skills, programming languages, frameworks, tools, and platforms. No soft skills. No project names. No company names. No domain topics.",
    "capabilities": "Comma separated list of professional capabilities demonstrated. Use standard terms like: team leadership, REST API design, microservices architecture, agile development, code review, system design, cloud deployment, database optimization. Maximum 6 items."
}}

Rules:
- Skills must be technical only — Python, React, AWS, Docker, PostgreSQL etc
- Do NOT include project names, company names, or domain words like traffic or payments
- Capabilities describe HOW they work, not WHAT they worked on
- Return ONLY the JSON object — no explanation, no markdown, no extra text

CV TEXT:
{cv_text}
"""


def extract_with_llm(raw_text: str) -> dict:
    """
    Extract clean, job-description-vocabulary fields from CV.
    No project domains, no company names, no irrelevant words.
    """
    prompt = EXTRACTION_PROMPT.format(cv_text=raw_text[:4000])

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are an expert HR analyst. Always return valid JSON only. No markdown, no explanation."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1,
        max_tokens=500
    )

    content = response.choices[0].message.content.strip()

    # Clean markdown fences if model adds them
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()

    extracted = json.loads(content)

    # Validate required fields
    for field in ["role_title", "experience_years", "experience_level", "skills", "capabilities"]:
        if field not in extracted:
            raise ValueError(f"Missing field in LLM response: {field}")

    return extracted


def build_embedding_text(extracted: dict) -> dict:
    """
    Construct clean embedding texts from extracted fields.
    Uses only job-description vocabulary — no project domains.

    Returns dict with skills and experience keys
    matching what embedder.py expects.
    """

    # Skills vector text — pure technical skills only
    skills_text = extracted["skills"]

    # Profile vector text — constructed from clean fields
    # This sounds exactly like a job description would
    profile_text = (
        f"{extracted['experience_level'].capitalize()} {extracted['role_title']} "
        f"with {extracted['experience_years']} years of experience. "
        f"Skills: {extracted['skills']}. "
        f"Capabilities: {extracted['capabilities']}."
    )

    return {
        "skills": skills_text,
        "experience": profile_text,
        # Summary combines both for a rich but clean vector
        "summary": profile_text + " " + skills_text
    }


def parse_cv_smart(
    raw_text: str,
    fallback_skills: list = None,
    fallback_experience: str = ""
) -> dict:
    """
    Smart CV parser — LLM first, rule-based fallback.

    LLM extracts clean structured fields then constructs
    job-description-vocabulary embedding texts.
    No project domains or irrelevant words in the vectors.
    """

    # --- Try LLM extraction ---
    try:
        print("[INFO] Attempting LLM-based CV extraction...")

        extracted = extract_with_llm(raw_text)

        print(f"[INFO] LLM extracted:")
        print(f"  Role: {extracted['role_title']}")
        print(f"  Level: {extracted['experience_level']} ({extracted['experience_years']} years)")
        print(f"  Skills: {extracted['skills'][:80]}...")
        print(f"  Capabilities: {extracted['capabilities']}")

        sections = build_embedding_text(extracted)

        print("[INFO] Embedding texts constructed successfully")
        return sections

    except Exception as e:
        print(f"[WARN] LLM extraction failed: {e} — falling back to rule-based parser")

    # --- Fallback ---
    sections = parse_cv_sections(
        raw_text=raw_text,
        fallback_skills=fallback_skills,
        fallback_experience=fallback_experience
    )

    print("[INFO] Rule-based fallback completed")
    return sections