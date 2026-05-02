# ============================================
# FaultAI — PDF PROCESSOR
# Extracts text from PDF books and splits
# into chunks for RAG retrieval.
#
# This module handles:
#   1. Extracting text from PDF (page-by-page)
#   2. OCR fallback for scanned/image-based PDFs
#   3. Splitting text into overlapping chunks
#   4. Caching chunks to avoid re-parsing
# ============================================

import fitz  # PyMuPDF
import json
import os
import re
import hashlib


# ── Optional OCR imports (only needed for scanned PDFs) ──
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


class PdfProcessor:
    """
    PDF Text Processor for RAG Pipeline.

    Extracts text from a PDF book, splits it into
    overlapping chunks suitable for TF-IDF retrieval,
    and caches the result for fast startup.

    For scanned PDFs (image-only), falls back to real
    OCR via pytesseract + pdf2image.
    """

    def __init__(self, pdf_path, chunk_size=500, chunk_overlap=100):
        """
        Args:
            pdf_path (str):       Path to the PDF file
            chunk_size (int):     Target words per chunk (~500)
            chunk_overlap (int):  Overlap words between chunks (~100)
        """
        self.pdf_path = pdf_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Cache file sits next to the PDF
        self.cache_path = os.path.splitext(pdf_path)[0] + "_chunks.json"

    # ──────────────────────────────────────────────
    # PUBLIC
    # ──────────────────────────────────────────────

    def get_chunks(self):
        """
        Get text chunks from the PDF.
        Uses cache if available and PDF hasn't changed.

        Returns:
            list[dict]: List of chunks, each with:
                - chunk_id (int)
                - text (str)
                - page_start (int)
                - page_end (int)
        """
        # ── Try loading from cache ──
        if self._cache_is_valid():
            print("[CACHE] Loading PDF chunks from cache...")
            return self._load_cache()

        # ── Extract fresh from PDF ──
        print(f"[INFO] Extracting text from PDF: {os.path.basename(self.pdf_path)}")
        pages = self._extract_pages()
        chunks = self._split_into_chunks(pages)

        # ── Save cache ──
        if chunks:
            self._save_cache(chunks)

        return chunks

    # ──────────────────────────────────────────────
    # EXTRACTION
    # ──────────────────────────────────────────────

    def _extract_pages(self):
        """
        Extract text from each page of the PDF.
        Tries PyMuPDF first (fast), then falls back to
        real Tesseract OCR for scanned pages.

        Returns:
            list[dict]: Each entry has 'page_num' and 'text'
        """
        doc = fitz.open(self.pdf_path)
        pages = []
        total_pages = len(doc)
        empty_pages = []

        print(f"[INFO] Total pages: {total_pages}")

        for page_num in range(total_pages):
            page = doc[page_num]
            text = self._try_extract_text(page)

            if text:
                pages.append({"page_num": page_num + 1, "text": text})
            else:
                empty_pages.append(page_num)

            if (page_num + 1) % 50 == 0:
                print(f"[INFO] Processed {page_num + 1}/{total_pages} pages "
                      f"({len(pages)} with text so far)...")

        doc.close()

        print(f"[SUCCESS] Extracted text from {len(pages)} pages "
              f"(skipped {len(empty_pages)} empty/image-only pages)")

        # ── If nothing extracted, try full OCR ──
        if not pages:
            print("[WARNING] No text found in PDF — this appears to be a scanned document.")
            pages = self._extract_with_real_ocr()

        # ── If still nothing, warn clearly ──
        if not pages:
            print("[ERROR] Could not extract any text from this PDF.")
            print("[ERROR] Make sure pytesseract and poppler are installed for OCR support.")

        return pages

    def _try_extract_text(self, page):
        """
        Try three PyMuPDF extraction strategies on a single page.
        Returns cleaned text string, or empty string if all fail.
        """
        text = ""

        # Method 1: Standard text extraction
        text = page.get_text("text").strip()
        if len(text) >= 20:
            return self._clean(text)

        # Method 2: Block-based extraction
        blocks = page.get_text("blocks")
        if blocks:
            block_texts = [
                block[4].strip()
                for block in blocks
                if block[6] == 0 and block[4].strip()
            ]
            text = "\n".join(block_texts).strip()
            if len(text) >= 20:
                return self._clean(text)

        # Method 3: Raw dict (handles some embedded fonts)
        try:
            page_dict = page.get_text("rawdict")
            dict_texts = []
            for block in page_dict.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            span_text = span.get("text", "").strip()
                            if span_text:
                                dict_texts.append(span_text)
            text = " ".join(dict_texts).strip()
            if len(text) >= 20:
                return self._clean(text)
        except Exception:
            pass

        # Method 4: XHTML mode (handles some alternate encodings)
        try:
            xhtml = page.get_text("xhtml")
            plain = re.sub(r"<[^>]+>", " ", xhtml)
            plain = self._clean(plain)
            if len(plain) >= 20:
                return plain
        except Exception:
            pass

        return ""

    def _extract_with_real_ocr(self):
        """
        Full OCR extraction using Tesseract for scanned PDFs.
        Requires: pytesseract, pdf2image, Pillow, and poppler.

        Returns:
            list[dict]: Pages with OCR-extracted text
        """
        if not OCR_AVAILABLE:
            print("[ERROR] OCR libraries not installed.")
            print("[ERROR] Run: pip install pytesseract pdf2image Pillow")
            print("[ERROR] Also install Tesseract: https://github.com/tesseract-ocr/tesseract")
            print("[ERROR] Also install Poppler: https://poppler.freedesktop.org/")
            return []

        print("[OCR] Starting Tesseract OCR — this may take a while for large PDFs...")
        pages = []

        try:
            # Convert PDF pages to images (300 DPI for good accuracy)
            print("[OCR] Rendering PDF pages to images at 300 DPI...")
            images = convert_from_path(self.pdf_path, dpi=300)
            total = len(images)
            print(f"[OCR] Rendered {total} pages. Running OCR...")

            for i, image in enumerate(images):
                page_num = i + 1
                try:
                    # Run Tesseract OCR
                    # lang='eng' — change to your language if needed
                    text = pytesseract.image_to_string(image, lang="eng")
                    text = self._clean(text)

                    if len(text) >= 20:
                        pages.append({"page_num": page_num, "text": text})

                    if page_num % 10 == 0:
                        print(f"[OCR] Processed {page_num}/{total} pages "
                              f"({len(pages)} with text so far)...")

                except Exception as e:
                    print(f"[OCR] Warning: page {page_num} failed — {e}")
                    continue

            print(f"[OCR] Completed. Extracted text from {len(pages)}/{total} pages.")

        except Exception as e:
            print(f"[OCR] Fatal error during OCR: {e}")
            return []

        return pages

    # ──────────────────────────────────────────────
    # CHUNKING
    # ──────────────────────────────────────────────

    def _split_into_chunks(self, pages):
        """
        Split page text into overlapping word-based chunks.

        Each chunk is ~chunk_size words with chunk_overlap words
        of overlap with the next chunk, preserving page references.

        Returns:
            list[dict]: Chunks with text and page references
        """
        if not pages:
            return []

        chunks = []
        chunk_id = 0

        # Combine all pages into a stream of (word, page_num) pairs
        word_stream = []
        for page in pages:
            words = page["text"].split()
            for word in words:
                word_stream.append((word, page["page_num"]))

        if not word_stream:
            return []

        # Slide a window over the word stream
        step = max(1, self.chunk_size - self.chunk_overlap)
        i = 0
        while i < len(word_stream):
            end = min(i + self.chunk_size, len(word_stream))
            window = word_stream[i:end]

            chunk_text = " ".join(w[0] for w in window)
            page_start = window[0][1]
            page_end = window[-1][1]

            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "page_start": page_start,
                "page_end": page_end
            })

            chunk_id += 1
            i += step

        print(f"[SUCCESS] Created {len(chunks)} chunks "
              f"({self.chunk_size} words each, {self.chunk_overlap} word overlap)")
        return chunks

    # ──────────────────────────────────────────────
    # CACHE
    # ──────────────────────────────────────────────

    def _get_pdf_hash(self):
        """Get MD5 hash of PDF file to detect changes."""
        hasher = hashlib.md5()
        with open(self.pdf_path, "rb") as f:
            for block in iter(lambda: f.read(8192), b""):
                hasher.update(block)
        return hasher.hexdigest()

    def _cache_is_valid(self):
        """Check if cache exists and matches current PDF."""
        if not os.path.exists(self.cache_path):
            return False
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
            return cache.get("pdf_hash") == self._get_pdf_hash()
        except (json.JSONDecodeError, KeyError):
            return False

    def _load_cache(self):
        """Load chunks from cache file."""
        with open(self.cache_path, "r", encoding="utf-8") as f:
            cache = json.load(f)
        chunks = cache["chunks"]
        print(f"[SUCCESS] Loaded {len(chunks)} cached chunks")
        return chunks

    def _save_cache(self, chunks):
        """Save chunks to cache file with PDF hash."""
        cache = {
            "pdf_hash": self._get_pdf_hash(),
            "pdf_file": os.path.basename(self.pdf_path),
            "chunk_count": len(chunks),
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "chunks": chunks
        }
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
        print(f"[SUCCESS] Cache saved to {os.path.basename(self.cache_path)}")

    # ──────────────────────────────────────────────
    # UTILS
    # ──────────────────────────────────────────────

    @staticmethod
    def _clean(text):
        """Normalize whitespace in extracted text."""
        return " ".join(text.split())