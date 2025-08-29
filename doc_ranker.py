# doc_ranker.py
import math
from collections import defaultdict
from invertedindexer import InvertedIndexer  # flat folder import


class DocumentRanker:
    def __init__(self, indexer: InvertedIndexer):
        """
        Rank documents using TF-IDF weighted cosine similarity.
        :param indexer: an InvertedIndexer object with pre-built index and document vectors.
        """
        self.indexer = indexer
        print("[INIT] DocumentRanker created with loaded index.")
        print(f"[INFO] Index has {len(self.indexer.documents)} documents "
              f"and {len(self.indexer.inverted_index)} unique terms.")

    # -------------------------
    # Build query vector
    # -------------------------
    def calculate_query_vector(self, query_terms):
        """
        Construct a TF-IDF weighted query vector.
        Uses raw term frequencies (instead of uniform normalization)
        for sharper similarity scores.
        """
        query_vector = defaultdict(float)

        # Count raw term frequencies
        for term in query_terms:
            query_vector[term] += 1.0

        # Optional: log-scaling for balance
        # for term in query_vector:
        #     query_vector[term] = 1 + math.log(query_vector[term])

        # Apply IDF weights from the index
        for term in query_vector:
            idf = self.indexer.compute_inverse_document_frequency(term)
            query_vector[term] *= idf

        return query_vector

    # -------------------------
    # Cosine similarity
    # -------------------------
    def calculate_cosine_similarity(self, query_vector, document_vector):
        """
        Compute cosine similarity between query vector and a document vector.
        """
        common_terms = set(query_vector.keys()) & set(document_vector.keys())
        if not common_terms:
            return 0.0

        numerator = sum(query_vector[t] * document_vector[t] for t in common_terms)
        query_mag = math.sqrt(sum(w ** 2 for w in query_vector.values()))
        doc_mag = math.sqrt(sum(w ** 2 for w in document_vector.values()))

        if query_mag == 0.0 or doc_mag == 0.0:
            return 0.0

        return numerator / (query_mag * doc_mag)

    # -------------------------
    # Main ranking
    # -------------------------
    def rank_documents(self, query, top_n=None):
        """
        Rank documents by cosine similarity against the query.
        :param query: str, the search query
        :param top_n: int, optional, number of top results to return
        :return: list of dicts with document info + score
        """
        query_terms = self.indexer.preprocess_text(query)
        if not query_terms:
            return []

        query_vector = self.calculate_query_vector(query_terms)

        similarities = []
        for doc_id, doc_vector in self.indexer.document_vectors.items():
            score = self.calculate_cosine_similarity(query_vector, doc_vector)
            similarities.append((doc_id, score))

        ranked_docs = sorted(similarities, key=lambda x: x[1], reverse=True)

        results = []
        for doc_id, score in ranked_docs:
            doc_info = self.indexer.documents[doc_id].copy()
            doc_info['score'] = round(score, 4)  # limit to 4 decimals
            results.append(doc_info)

        if top_n:
            results = results[:top_n]

        return results


# -------------------------
# Optional standalone CLI for testing
# -------------------------
if __name__ == "__main__":
    indexer = InvertedIndexer()
    indexer.load_index()
    ranker = DocumentRanker(indexer)

    query = input("Enter your search query: ")
    top_n_input = input("How many results to show? [default 5]: ")

    try:
        top_n = int(top_n_input)
    except ValueError:
        top_n = 5

    results = ranker.rank_documents(query, top_n=top_n)

    print(f"\nTop {len(results)} results for query: '{query}'\n")
    for i, doc in enumerate(results, 1):
        print(f"{i}. {doc['title']} (Score={doc['score']})")
        print(f"   Authors: {', '.join(author['name'] for author in doc['authors'])}")
        print(f"   URL: {doc['url']}")
        print(f"   Date: {doc['date']}")
        if 'abstract' in doc:
            print(f"   Abstract: {doc['abstract'][:200]}...\n")
