import os
from pathlib import Path
from typing import Optional, List, Tuple

from pypdf import PdfReader


SYLLABUS_DIR = Path("storage/syllabus")
SYLLABUS_DIR.mkdir(parents=True, exist_ok=True)


def _read_pdf_text(file_path: Path) -> List[Tuple[int, str]]:
    """Return a list of (page_index, text) tuples for the given PDF."""
    reader = PdfReader(str(file_path))
    pages: List[Tuple[int, str]] = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append((i, text))
    return pages


def save_syllabus_pdf(file_bytes: bytes, filename: str = "syllabus.pdf") -> str:
    """Persist the uploaded syllabus PDF and return its file path."""
    safe_name = "".join(c for c in filename if c.isalnum() or c in (" ", "_", "-", "."))
    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"
    target = SYLLABUS_DIR / safe_name
    with open(target, "wb") as f:
        f.write(file_bytes)
    return str(target)


def get_latest_syllabus_path() -> Optional[Path]:
    """Return the most recently saved syllabus PDF path, if any."""
    pdfs = sorted(SYLLABUS_DIR.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
    return pdfs[0] if pdfs else None


def retrieve_topic_context(topic: str, module: Optional[str], subject: Optional[str], max_chars: int = 4000) -> Optional[str]:
    """Naive retrieval: search the syllabus PDF for topic/module/subject keywords and return concatenated snippets."""
    syllabus_path = get_latest_syllabus_path()
    if not syllabus_path:
        return None

    pages = _read_pdf_text(syllabus_path)
    if not pages:
        return None

    # Prepare keywords
    keys = [topic or ""]
    if module:
        keys.append(module)
    if subject:
        keys.append(subject)
    keys = [k.strip().lower() for k in keys if k and k.strip()]
    if not keys:
        return None

    # Score pages by keyword hits
    scored: List[Tuple[int, int, str]] = []  # (score, page_index, text)
    for page_index, text in pages:
        low = (text or "").lower()
        score = sum(low.count(k) for k in keys)
        if score > 0:
            scored.append((score, page_index, text))

    if not scored:
        # Fallback: search for the largest page containing any token from topic
        tokens = [t for t in (topic or "").lower().split() if len(t) > 3]
        for page_index, text in pages:
            low = (text or "").lower()
            score = sum(1 for t in tokens if t in low)
            if score > 0:
                scored.append((score, page_index, text))

    if not scored:
        return None

    # Sort by score and gather snippets until max_chars
    scored.sort(reverse=True)
    buffer: str = ""
    for score, page_index, text in scored:
        if not text:
            continue
        chunk = text.strip()
        if not chunk:
            continue
        # Add page separator
        addition = f"\n\n[Page {page_index + 1}]\n{chunk}"
        if len(buffer) + len(addition) > max_chars:
            remaining = max_chars - len(buffer)
            if remaining <= 0:
                break
            buffer += addition[:remaining]
            break
        buffer += addition

    return buffer.strip() or None





