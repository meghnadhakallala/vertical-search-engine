# invertedindexer.py
import json
import math
import pickle
from collections import defaultdict
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
import nltk
import os

# Download NLTK resources if not already available
nltk.download('punkt')
nltk.download('stopwords')


class InvertedIndexer:
    def __init__(self):
        self.inverted_index = defaultdict(list)  # term -> list of (doc_id, tf-idf)
        self.term_document_counts = defaultdict(int)  # term -> number of documents containing term
        self.document_vectors = {}  # doc_id -> {term: tf-idf}
        self.documents = []  # list of documents with metadata
        self.stemmer = PorterStemmer()
        self.stop_words = set(stopwords.words('english'))

    # -------------------------
    # Preprocessing
    # -------------------------
    def preprocess_text(self, text):
        tokens = word_tokenize(text.lower())
        tokens = [t for t in tokens if t.isalnum()]
        return [self.stemmer.stem(t) for t in tokens if t not in self.stop_words]

    # -------------------------
    # Compute IDF (for DocumentRanker compatibility)
    # -------------------------
    def compute_inverse_document_frequency(self, term):
        # Add +1 to denominator for smoothing (avoid div by zero)
        return math.log((len(self.documents) + 1) / (self.term_document_counts.get(term, 0) + 1)) + 1

    # -------------------------
    # Build index from JSON
    # -------------------------
    def build_index(self, json_file):
        print(f"[INFO] Loading documents from {json_file} ...")
        with open(json_file, 'r', encoding='utf-8') as f:
            publications = json.load(f)

        for doc_id, pub in enumerate(publications):
            # Combine title + abstract + authors
            authors_text = " ".join([a['name'] for a in pub.get('authors', [])])
            combined_text = f"{pub.get('title','')} {pub.get('abstract','')} {authors_text}"
            tokens = self.preprocess_text(combined_text)

            self.documents.append({
                'id': doc_id,
                'title': pub.get('title',''),
                'url': pub.get('url',''),
                'date': pub.get('date',''),
                'authors': pub.get('authors', []),
                'abstract': pub.get('abstract','')
            })

            # Count raw term frequencies
            term_counts = defaultdict(int)
            for token in tokens:
                term_counts[token] += 1

            # Track how many docs contain each term
            for token in set(tokens):
                self.term_document_counts[token] += 1

            # Build TF (log-scaled) vector
            tf_vector = {}
            for term, count in term_counts.items():
                tf = 1 + math.log(count)   # log-scaling
                tf_vector[term] = tf
                self.inverted_index[term].append((doc_id, tf))  # temporarily store TF

            self.document_vectors[doc_id] = tf_vector

        # Convert TF -> TF-IDF
        print("[INFO] Converting TF to TF-IDF...")
        for term, postings in self.inverted_index.items():
            idf = self.compute_inverse_document_frequency(term)
            for i, (doc_id, tf) in enumerate(postings):
                self.inverted_index[term][i] = (doc_id, tf * idf)
                self.document_vectors[doc_id][term] *= idf

        print(f"[INFO] Indexed {len(self.documents)} documents with {len(self.inverted_index)} unique terms.")

    # -------------------------
    # Save / Load index
    # -------------------------
    def save_index(self, filename="inverted_index.pkl"):
        data = {
            'inverted_index': dict(self.inverted_index),
            'term_document_counts': dict(self.term_document_counts),
            'document_vectors': self.document_vectors,
            'documents': self.documents
        }
        with open(filename, 'wb') as f:
            pickle.dump(data, f)
        print(f"[INFO] Index saved to {filename}")

    def load_index(self, filename="inverted_index.pkl"):
        with open(filename, 'rb') as f:
            data = pickle.load(f)
        self.inverted_index = defaultdict(list, data['inverted_index'])
        self.term_document_counts = defaultdict(int, data['term_document_counts'])
        self.document_vectors = data['document_vectors']
        self.documents = data['documents']
        print(f"[INFO] Index loaded from {filename}")


# -------------------------
# Standalone run
# -------------------------
if __name__ == "__main__":
    JSON_FILE = "coventry_publications.json"  # Ensure your crawler has produced this
    indexer = InvertedIndexer()
    indexer.build_index(JSON_FILE)
    indexer.save_index()
 