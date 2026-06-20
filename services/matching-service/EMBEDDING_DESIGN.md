# Embedding Design — Matching Service
**Author:** W.D.S.R. Rudrigo (21/ENG/118)  
**Last Updated:** May 2026

---

## Why Embeddings?

Normal keyword search fails when a job says "Python developer" 
and a candidate writes "Django engineer" — exact words don't match 
even though the meaning is the same.

Embeddings convert text into 384 numbers that represent **meaning**, 
not just words. Similar meanings produce vectors that are 
mathematically close. This is how we match candidates to jobs 
accurately even when the exact words differ.

---

## Model Used

**Model:** `all-MiniLM-L6-v2` (sentence-transformers)  
**Output dimensions:** 384  
**Similarity metric:** Cosine similarity  

Chosen because:
- Lightweight and fast (runs without GPU)
- Strong performance on short text like skills and job titles
- Free and open source

---

## Vector Strategy — 3 Vectors Per Candidate

Each candidate has 3 vectors stored in Pinecone:

| Vector ID | Input Text | Purpose |
|---|---|---|
| `{phone}_skills_v1` | "Python, React, PostgreSQL" | Match technical skills |
| `{phone}_experience_v1` | "3 years backend at startup" | Match experience level |
| `{phone}_summary_v1` | Full CV text (first 2000 chars) | Match overall profile |

### Why 3 vectors instead of 1?

One combined vector loses precision. Separating skills from 
experience allows different job requirements to match against 
the most relevant vector:

- Job requiring "Python" → strong match on skills vector
- Job requiring "startup experience" → strong match on experience vector

---

## Matching Threshold

**SIMILARITY_THRESHOLD = 0.72**

- Score above 0.72 → candidate is notified
- Score below 0.72 → candidate is skipped
- Maximum 20 candidates notified per job posting

This value was chosen to balance precision vs recall.
Can be tuned based on real data in later phases.

---

## Vector IDs
{phone}_skills_v1
{phone}_experience_v1
{phone}summary_v1
job{job_id}

Phone number is used as the unique identifier because candidates 
register via WhatsApp — no username or email exists at registration time.

---

## Integration Points

| Team Member | What They Need to Know |
|---|---|
| Lakshan | When CV is uploaded → publish to `cv.uploaded` SQS queue with phone, skills, experience, full_text fields |
| Sivabalasri | When onboarding completes → trigger cv.uploaded event. Matching happens automatically after that |

---

## SQS Event Format Expected

```json
{
  "phone": "94771234567",
  "skills": ["Python", "React", "SQL"],
  "experience": "3 years backend developer at tech startup",
  "full_text": "Full CV text here..."
}
```