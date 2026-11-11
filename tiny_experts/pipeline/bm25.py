import math
import re
from collections import Counter
from typing import List, Dict, Any, Optional

class BM25Retriever:
    """
    Okapi BM25 Probabilistic Ranking Retrieval Engine.
    Implements term frequency saturation, inverse document frequency (IDF),
    and document length normalization on local CPU with sub-millisecond execution.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size: int = 0
        self.avg_doc_len: float = 0.0
        self.doc_lengths: List[int] = []
        self.doc_term_freqs: List[Counter] = []
        self.df: Counter = Counter()
        self.idf: Dict[str, float] = {}
        self.documents: List[Dict[str, Any]] = []

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Extracts normalized lowercase alphanumeric tokens."""
        return re.findall(r"\b[a-zA-Z0-9_\-]+\b", text.lower())

    def index_documents(self, documents: List[Dict[str, Any]]):
        """
        Builds the BM25 statistical index across all passages in the corpus.
        Each document dict must have a 'text' key.
        """
        self.documents = documents
        self.corpus_size = len(documents)
        self.doc_lengths = []
        self.doc_term_freqs = []
        self.df = Counter()
        self.idf = {}

        if self.corpus_size == 0:
            self.avg_doc_len = 0.0
            return

        total_words = 0
        for doc in documents:
            tokens = self.tokenize(doc.get("text", ""))
            doc_len = len(tokens)
            self.doc_lengths.append(doc_len)
            total_words += doc_len

            term_freq = Counter(tokens)
            self.doc_term_freqs.append(term_freq)

            # Document frequency: count unique terms per document
            for term in term_freq.keys():
                self.df[term] += 1

        self.avg_doc_len = total_words / self.corpus_size if self.corpus_size > 0 else 0.0

        # Calculate Okapi BM25 IDF for each term: ln(1 + (N - n + 0.5) / (n + 0.5))
        for term, freq in self.df.items():
            self.idf[term] = math.log(1.0 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def search(
        self,
        query: str,
        shelf_filter: Optional[str] = None,
        top_k: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Calculates Okapi BM25 scores for the query against indexed passages.
        Returns the top_k ranked passages with their BM25 score.
        """
        q_tokens = self.tokenize(query)
        if not q_tokens or self.corpus_size == 0:
            return []

        scores: List[tuple[float, int]] = []

        for idx, doc in enumerate(self.documents):
            # Optional shelf filtering
            if shelf_filter and doc.get("shelf") != shelf_filter:
                continue

            doc_len = self.doc_lengths[idx]
            term_freqs = self.doc_term_freqs[idx]

            if doc_len == 0:
                continue

            len_norm = 1.0 - self.b + self.b * (doc_len / self.avg_doc_len) if self.avg_doc_len > 0 else 1.0
            score = 0.0

            for q_term in q_tokens:
                if q_term not in term_freqs:
                    continue

                tf = term_freqs[q_term]
                idf = self.idf.get(q_term, 0.0)

                # Standard BM25 term weighting
                term_score = idf * (tf * (self.k1 + 1.0)) / (tf + self.k1 * len_norm)
                score += term_score

            if score > 0.0:
                scores.append((score, idx))

        scores.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, idx in scores[:top_k]:
            doc_copy = dict(self.documents[idx])
            doc_copy["bm25_score"] = round(score, 3)
            results.append(doc_copy)

        return results
