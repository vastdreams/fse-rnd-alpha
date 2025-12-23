"""
PATH: src/ingestion/annual_report_text_extractor.py
PURPOSE:
  - Extract and chunk annual report text from HTML/PDF/TXT (SEC submissions) for downstream AI processing.
ROLE IN ARCHITECTURE:
  - Ingestion layer: converts raw filings into clean, section-aware text chunks.
MAIN EXPORTS:
  - extract_report_text(): entry point that routes to HTML/PDF/TXT extractors.
NON-RESPONSIBILITIES:
  - Does not download filings or manage storage.
  - Does not perform financial/R&D extraction itself.
NOTES FOR FUTURE AI:
  - When SEC submissions are .txt, prefer the primary 10-K DOCUMENT and drop exhibits/XBRL noise before chunking.
  - Keep chunks small to avoid GPT token blowups; adjust max words here, not in callers.
"""
from pathlib import Path
from typing import List, Dict
from bs4 import BeautifulSoup
import pdfplumber
from src.logging.logger import get_logger

logger = get_logger(__name__)


def _chunk_by_words(
    paragraphs: List[str],
    section_patterns,
    max_words_per_chunk: int = 900,
    min_words_per_chunk: int = 60,
) -> List[Dict]:
    """Chunk paragraphs into reasonably sized sections with section detection."""
    import re

    text_blocks = []
    current_section = "unknown"
    current_section_title = None
    current_page = 1
    current_text: List[str] = []

    def flush_chunk():
        if not current_text:
            return
        chunk_text = "\n".join(current_text).strip()
        if not chunk_text:
            current_text.clear()
            return
        words = chunk_text.split()
        if len(words) < min_words_per_chunk:
            # keep tiny chunks only if nothing else exists
            if not text_blocks:
                text_blocks.append({
                    "page": current_page,
                    "section": current_section,
                    "section_title": current_section_title,
                    "text": chunk_text,
                })
            current_text.clear()
            return
        text_blocks.append({
            "page": current_page,
            "section": current_section,
            "section_title": current_section_title,
            "text": chunk_text,
        })
        current_text.clear()

    for para in paragraphs:
        # Section detection
        section_found = False
        for pattern in section_patterns:
            match = re.search(pattern, para, re.IGNORECASE)
            if match:
                flush_chunk()
                if "Item" in pattern:
                    current_section = f"Item {match.group(1)}"
                    current_section_title = match.group(2) if len(match.groups()) > 1 else None
                else:
                    current_section = match.group(1).lower().replace(" ", "_")
                    current_section_title = match.group(1)
                section_found = True
                break
        if section_found:
            continue

        current_text.append(para)
        word_count = sum(len(p.split()) for p in current_text)
        if word_count >= max_words_per_chunk:
            flush_chunk()

    flush_chunk()
    return text_blocks


def extract_text_from_html(file_path: Path) -> List[Dict]:
    """
    Extract text from HTML file with page markers and section identification.
    
    Uses multiple parser fallbacks for robustness.
    """
    if not file_path.exists():
        logger.error(f"File does not exist: {file_path}")
        return []
    
    if not file_path.is_file():
        logger.error(f"Path is not a file: {file_path}")
        return []
    
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except PermissionError as e:
        logger.error(f"Permission denied reading file {file_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return []
    
    # Try multiple parsers in order of preference
    soup = None
    parsers = ["lxml", "html.parser", "html5lib"]
    
    for parser in parsers:
        try:
            soup = BeautifulSoup(content, parser)
            logger.debug(f"Successfully parsed HTML with {parser} parser")
            break
        except Exception as e:
            logger.warning(f"Failed to parse with {parser} parser: {e}")
            continue
    
    if soup is None:
        logger.error(f"Failed to parse HTML with any parser: {file_path}")
        return []
    
    try:
        # Remove script, style, and common hidden elements (inline XBRL headers/hidden)
        for tag in soup(["script", "style"]):
            tag.decompose()
        for tag in soup.find_all(["ix:header", "ix:hidden"]):
            tag.decompose()
        for tag in soup.find_all(style=True):
            style = tag.get("style", "").lower()
            if "display:none" in style or "visibility:hidden" in style:
                tag.decompose()

        import re
        section_patterns = [
            r"Item\s+(\d+[A-Z]?)\s*[:\-]?\s*(.+)",  # Item 1, Item 7, Item 7A, etc.
            r"PART\s+[IVX]+\s*[:\-]?\s*(.+)",  # PART I, PART II, etc.
            r"(Management['']?s?\s+Discussion\s+and\s+Analysis)",  # MD&A
            r"(Risk\s+Factors?)",
            r"(Business\s+Overview)",
        ]

        # Block-based extraction
        blocks = []
        for el in soup.find_all(["p", "div", "li", "td", "th", "span", "h1", "h2", "h3", "h4"]):
            text = " ".join(el.stripped_strings)
            # Keep smaller fragments now; filter later in chunking
            if len(text) < 10:
                continue
            blocks.append(text)

        text_blocks = _chunk_by_words(
            blocks,
            section_patterns,
            max_words_per_chunk=900,
            min_words_per_chunk=60,
        )

        # Fallback: if too few chunks, use full visible text paragraphs
        if len(text_blocks) < 3:
            full_text = soup.get_text(separator="\n")
            paragraphs = [p.strip() for p in full_text.split("\n") if p.strip()]
            text_blocks = _chunk_by_words(
                paragraphs,
                section_patterns,
                max_words_per_chunk=900,
                min_words_per_chunk=40,
            )

        return text_blocks
    
    except Exception as e:
        logger.error(f"Error extracting text from HTML {file_path}: {e}")
        return []


def extract_text_from_pdf(file_path: Path) -> List[Dict]:
    """
    Extract text from PDF file with page markers.
    
    Validates PDF before extraction and handles errors gracefully.
    """
    if not file_path.exists():
        logger.error(f"File does not exist: {file_path}")
        return []
    
    if not file_path.is_file():
        logger.error(f"Path is not a file: {file_path}")
        return []
    
    # Validate file size (PDFs should have reasonable size)
    try:
        file_size = file_path.stat().st_size
        if file_size == 0:
            logger.error(f"PDF file is empty: {file_path}")
            return []
        if file_size > 100 * 1024 * 1024:  # > 100MB
            logger.warning(f"PDF file is very large ({file_size / (1024*1024):.1f} MB): {file_path}")
    except Exception as e:
        logger.error(f"Error checking PDF file size: {e}")
        return []
    
    try:
        text_blocks = []
        
        # Validate PDF before opening
        try:
            with open(file_path, "rb") as f:
                header = f.read(4)
                if not header.startswith(b"%PDF"):
                    logger.error(f"File does not appear to be a valid PDF: {file_path}")
                    return []
        except Exception as e:
            logger.error(f"Error validating PDF header: {e}")
            return []
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    text_blocks.append({
                        "page": page_num,
                        "text": text,
                    })
        
        return text_blocks
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF {file_path}: {e}")
        return []


def extract_report_text(file_path: Path) -> List[Dict]:
    """Extract text from annual report (HTML or PDF)."""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    if suffix == ".txt":
        return extract_text_from_submission_txt(file_path)
    else:
        return extract_text_from_html(file_path)


def _split_submission_documents(content: str):
    """Split an SEC complete submission .txt into documents with TYPE metadata."""
    import re
    docs = []
    for match in re.finditer(r"(?is)<document>(.*?)</document>", content):
        block = match.group(1)
        type_match = re.search(r"(?im)^\s*<type>\s*([^\n<]+)", block)
        doc_type = type_match.group(1).strip() if type_match else "unknown"
        text_match = re.search(r"(?is)<text>(.*?)</text>", block)
        text_body = text_match.group(1) if text_match else block
        docs.append({"type": doc_type, "text": text_body})
    return docs


def extract_text_from_submission_txt(file_path: Path) -> List[Dict]:
    """
    Extract text from SEC complete submission .txt:
    - pick primary 10-K document (skip exhibits)
    - strip inline XBRL tags
    - aggressively chunk to avoid GPT token overload.
    """
    import re

    if not file_path.exists():
        logger.error(f"File does not exist: {file_path}")
        return []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logger.error(f"Error reading text file {file_path}: {e}")
        return []

    documents = _split_submission_documents(content)
    if not documents:
        logger.warning(f"No <DOCUMENT> blocks found in {file_path}, falling back to plain chunking")
        paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
        section_patterns = [
            r"Item\\s+(\\d+[A-Z]?)\\s*[:\\-]?\\s*(.+)",
            r"PART\\s+[IVX]+\\s*[:\\-]?\\s*(.+)",
            r"(Management['']?s?\\s+Discussion\\s+and\\s+Analysis)",
            r"(Risk\\s+Factors?)",
            r"(Business\\s+Overview)",
        ]
        return _chunk_by_words(
            paragraphs,
            section_patterns,
            max_words_per_chunk=600,
            min_words_per_chunk=40,
        )

    # Select primary 10-K doc; fallback to largest non-exhibit
    main_docs = [d for d in documents if "10-k" in d["type"].lower()]
    if not main_docs:
        non_exhibits = [d for d in documents if not d["type"].lower().startswith("ex-")]
        main_doc = max(non_exhibits, key=lambda d: len(d["text"]), default=documents[0])
    else:
        main_doc = max(main_docs, key=lambda d: len(d["text"]))

    text_body = main_doc["text"]

    # Parse as HTML where possible to unwrap XBRL tags but keep text
    soup = None
    for parser in ["lxml", "html.parser"]:
        try:
            soup = BeautifulSoup(text_body, parser)
            break
        except Exception:
            continue

    cleaned_text = ""
    if soup:
        # Drop script/style
        for tag in soup(["script", "style"]):
            tag.decompose()
        # Unwrap namespace tags (us-gaap:, ix:) to keep inner text but remove markup
        for tag in soup.find_all(True):
            if ":" in tag.name:
                tag.unwrap()
        cleaned_text = soup.get_text(separator="\n")
    else:
        # Fallback: strip XBRL tags crudely
        cleaned_text = re.sub(r"<[^>]+>", " ", text_body)

    # Normalize whitespace
    cleaned_lines = [line.strip() for line in cleaned_text.split("\n")]
    paragraphs = [p for p in cleaned_lines if p]

    # Split very long paragraphs to avoid massive chunks
    split_paragraphs: List[str] = []
    for p in paragraphs:
        words = p.split()
        if len(words) > 300:
            # split by sentence boundaries as a simple heuristic
            sentences = re.split(r"(?<=[\\.!?])\\s+", p)
            buf = []
            for sent in sentences:
                buf.append(sent)
                if sum(len(x.split()) for x in buf) >= 200:
                    split_paragraphs.append(" ".join(buf))
                    buf = []
            if buf:
                split_paragraphs.append(" ".join(buf))
        else:
            split_paragraphs.append(p)

    # Drop structured/XBRL-heavy paragraphs that are mostly tags or identifiers
    filtered_paragraphs: List[str] = []
    for p in split_paragraphs:
        lower = p.lower()
        if any(ns in lower for ns in ["us-gaap:", "dei:", "srt:", "xbrl", "ixt:", "ix:", "pg:"]):
            continue
        tokens = p.split()
        colon_tokens = sum(1 for t in tokens if ":" in t)
        if tokens and colon_tokens / len(tokens) > 0.3:
            continue
        digit_ratio = sum(c.isdigit() for c in p) / max(len(p), 1)
        if digit_ratio > 0.4:
            continue
        alpha_ratio = sum(c.isalpha() for c in p) / max(len(p), 1)
        printable_ratio = sum(c.isprintable() for c in p) / max(len(p), 1)
        if alpha_ratio < 0.05 or printable_ratio < 0.8:
            continue
        filtered_paragraphs.append(p)

    section_patterns = [
        r"Item\\s+(\\d+[A-Z]?)\\s*[:\\-]?\\s*(.+)",
        r"PART\\s+[IVX]+\\s*[:\\-]?\\s*(.+)",
        r"(Management['']?s?\\s+Discussion\\s+and\\s+Analysis)",
        r"(Risk\\s+Factors?)",
        r"(Business\\s+Overview)",
    ]

    return _chunk_by_words(
        filtered_paragraphs,
        section_patterns,
        max_words_per_chunk=500,
        min_words_per_chunk=40,
    )

