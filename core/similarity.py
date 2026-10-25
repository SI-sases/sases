from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def is_similar(new_desc, existing_descs, threshold=0.30):
    """使用字符级 TF-IDF 余弦相似度判断是否重复"""
    if not existing_descs:
        return False
    corpus = existing_descs + [new_desc]
    vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 3))
    try:
        existing_vecs = vectorizer.fit_transform(existing_descs)
        new_vec = vectorizer.transform([new_desc])
        sims = cosine_similarity(new_vec, existing_vecs).flatten()
        return bool((sims > threshold).any())
    except Exception as e:
        print(f"相似度计算异常: {e}")
        return False
