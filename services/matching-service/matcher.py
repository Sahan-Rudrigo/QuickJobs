from embedder import embed_text, index

SIMILARITY_THRESHOLD         = 0.72
REVERSE_SIMILARITY_THRESHOLD = 0.70  # Slightly lower for candidate → job direction
TOP_N = 20


def find_matching_candidates(job_id: str, title: str, skills: list, description: str) -> list:
    """
    Given a job posting, find the most relevant candidates from Pinecone.
    Returns a list of matched candidate phone numbers.
    """

    # Convert job into a vector
    combined = f"{title}. Skills needed: {', '.join(skills)}. {description}"
    job_vector = embed_text(combined)

    # Search Pinecone for similar candidate vectors
    results = index.query(
        vector=job_vector,
        top_k=TOP_N * 3,  # fetch more, filter below threshold after
        include_metadata=True
    )

    # Filter by similarity threshold
    matches = [
        r for r in results.matches
        if r.score >= SIMILARITY_THRESHOLD
    ]

    # Extract unique phone numbers from metadata
    phones = list({
        r.metadata["phone"]
        for r in matches[:TOP_N]
        if "phone" in r.metadata
    })

    return phones


def find_matching_jobs(phone: str, skills: list, experience: str, full_text: str) -> list:
    """
    Reverse matching: given a candidate's profile, find active job IDs from Pinecone.
    Job vectors are identified by 'job_id' in metadata (no 'phone' key).
    Called by the SQS consumer after a CV is embedded.
    """
    combined        = f"{experience}. Skills: {', '.join(skills)}. {full_text[:500]}"
    candidate_vector = embed_text(combined)

    results = index.query(
        vector=candidate_vector,
        top_k=10,
        include_metadata=True,
    )

    return list({
        r.metadata["job_id"]
        for r in results.matches
        if r.score >= REVERSE_SIMILARITY_THRESHOLD and "job_id" in r.metadata
    })



