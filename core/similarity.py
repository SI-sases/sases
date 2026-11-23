from .text_similarity import best_similarity


def is_similar(new_desc, existing_descs, threshold=0.30):
    """Character n-gram cosine similarity, no sklearn dependency."""
    if not existing_descs:
        return False
    try:
        return best_similarity(new_desc, existing_descs) > threshold
    except Exception as exc:
        print(f"similarity error: {exc}")
        return False
