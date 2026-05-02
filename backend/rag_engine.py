# ============================================
# FaultAI — RAG ENGINE (PDF-Based)
# Retrieval-Augmented Generation Module
#
# This module handles:
#   1. Loading text chunks from PDF book
#   2. Building TF-IDF index over all chunks
#   3. Finding the most relevant passages
#      based on user-provided symptoms
# ============================================

import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pdf_processor import PdfProcessor


class RAGEngine:
    """
    RAG (Retrieval-Augmented Generation) Engine — PDF Based

    Uses TF-IDF vectorization + cosine similarity to find
    the most relevant text passages from a PDF book
    based on user symptoms.
    """

    def __init__(self, pdf_path):
        """
        Initialize RAG engine with a PDF book.

        Args:
            pdf_path (str): Path to the PDF knowledge base
        """
        # ── Process PDF into chunks ──
        self.pdf_path = pdf_path
        self.processor = PdfProcessor(
            pdf_path=pdf_path,
            chunk_size=500,       # ~500 words per chunk
            chunk_overlap=100     # 100-word overlap between chunks
        )
        self.chunks = self.processor.get_chunks()

        # ── Build TF-IDF Index ──
        self.vectorizer = TfidfVectorizer(
            stop_words="english",       # Remove common words (the, is, at...)
            ngram_range=(1, 2),         # Use single words + word pairs
            max_features=10000          # Larger vocabulary for book content
        )
        self._build_index()

        print(f"✅ RAG Engine initialized with {len(self.chunks)} chunks from PDF")

    def _build_index(self):
        """
        Build TF-IDF vectors for all chunks from the PDF.
        """
        if not self.chunks:
            print("⚠️ No chunks found — TF-IDF index not built")
            return

        # Extract text from each chunk
        self.documents = [chunk["text"] for chunk in self.chunks]

        # Fit the TF-IDF vectorizer on all chunks
        self.tfidf_matrix = self.vectorizer.fit_transform(self.documents)
        print(f"📊 TF-IDF index built: {self.tfidf_matrix.shape}")

    def retrieve(self, query, category=None, top_k=5):
        """
        Retrieve the most relevant PDF passages for a given query.

        Args:
            query (str):      User's symptom description
            category (str):   Optional category filter (for future use)
            top_k (int):      Number of results to return

        Returns:
            list[dict]: Top matching passages with similarity scores.
                Each dict contains:
                - chunk_id (int)
                - text (str)
                - page_start (int)
                - page_end (int)
                - similarity_score (float)
        """
        if not self.chunks:
            return []

        # ── Convert query to TF-IDF vector ──
        query_vector = self.vectorizer.transform([query])

        # ── Calculate cosine similarity with all chunks ──
        similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()

        # ── Build results with scores ──
        results = []
        for idx, score in enumerate(similarities):
            if score > 0.01:  # Filter out near-zero matches
                chunk = self.chunks[idx].copy()
                chunk["similarity_score"] = round(float(score) * 100, 1)
                results.append(chunk)

        # ── Sort by similarity (highest first) ──
        results.sort(key=lambda x: x["similarity_score"], reverse=True)

        # ── Return top-K results ──
        return results[:top_k]

    def get_all_chunks(self):
        """Return all chunks with preview text (for Knowledge Base page)."""
        previews = []
        for chunk in self.chunks:
            previews.append({
                "chunk_id": chunk["chunk_id"],
                "preview": chunk["text"][:200] + "...",
                "page_start": chunk["page_start"],
                "page_end": chunk["page_end"],
                "word_count": len(chunk["text"].split())
            })
        return previews

    def get_chunk_count(self):
        """Return total number of chunks."""
        return len(self.chunks)

    def get_source_info(self):
        """Return info about the PDF source."""
        return {
            "filename": os.path.basename(self.pdf_path),
            "total_chunks": len(self.chunks),
            "chunk_size": self.processor.chunk_size,
            "chunk_overlap": self.processor.chunk_overlap
        }