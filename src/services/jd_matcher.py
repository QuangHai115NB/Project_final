from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def match_cv_to_jd(cv_text: str, jd_text: str) -> float:
    """
    So khớp CV với JD bằng TF-IDF + Cosine Similarity.
    Trả về điểm tương đồng (0 đến 1).
    """
    documents = [cv_text, jd_text]
    tfidf = TfidfVectorizer(stop_words="english")
    tfidf_matrix = tfidf.fit_transform(documents)
    cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
    return cosine_sim[0][0]