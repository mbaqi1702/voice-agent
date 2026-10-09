"""
Document loading utilities.
Supports PDF, DOCX, TXT, Markdown.
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger


def load_text_from_file(path: Path) -> str:
    """Extract plain text from a supported file."""
    suffix = path.suffix.lower()

    if suffix in {".txt", ".md", ".markdown"}:
        return path.read_text(encoding="utf-8", errors="ignore")

    if suffix == ".pdf":
        return _load_pdf(path)

    if suffix in {".docx", ".doc"}:
        return _load_docx(path)

    raise ValueError(f"Unsupported file type: {suffix}")


def _load_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"--- Page {i + 1} ---\n{text}")
        return "\n\n".join(pages)
    except Exception as e:
        logger.error(f"PDF extraction failed for {path}: {e}")
        raise


def _load_docx(path: Path) -> str:
    try:
        from docx import Document
        doc = Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except Exception as e:
        logger.error(f"DOCX extraction failed for {path}: {e}")
        raise


def save_uploaded_file(filename: str, content: bytes, documents_dir: Path) -> Path:
    """Save raw bytes to the documents directory and return the path."""
    documents_dir.mkdir(parents=True, exist_ok=True)
    dest = documents_dir / filename
    dest.write_bytes(content)
    logger.info(f"Saved document: {dest}")
    return dest
