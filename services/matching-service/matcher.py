from embedder import embed_text, index

# Minimum similarity score to consider a match
SIMILARITY_THRESHOLD = 0.72

# Maximum candidates to notify per job
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



