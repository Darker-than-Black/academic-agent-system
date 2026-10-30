"""Full-text index over extracted page text (SQLite FTS5, stdlib ``sqlite3``).

The index at ``.rh/library.sqlite`` is gitignored and rebuildable from the
``sources/pagetext/*.jsonl`` files (``rh library index``). FTS5 is used when the
local SQLite has it; otherwise a plain table with ``LIKE`` is the fallback so the
command never hard-fails on a stripped SQLite build.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from research_harness.library.extract import load_pagetext


def index_path(root: Path) -> Path:
    return root / ".rh" / "library.sqlite"


def pagetext_dir(root: Path) -> Path:
    return root / "sources" / "pagetext"


def _has_fts5(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE _fts_probe USING fts5(x)")
        conn.execute("DROP TABLE _fts_probe")
        return True
    except sqlite3.OperationalError:
        return False


def build_index(root: Path) -> int:
    """(Re)build the index from every pagetext file. Returns the page count."""
    path = index_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    conn = sqlite3.connect(path)
    try:
        fts = _has_fts5(conn)
        if fts:
            conn.execute(
                "CREATE VIRTUAL TABLE pages USING fts5(source_id, pdf_page, printed_page, text)"
            )
        else:
            conn.execute(
                "CREATE TABLE pages (source_id TEXT, pdf_page INTEGER, "
                "printed_page TEXT, text TEXT)"
            )
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO meta VALUES ('fts', ?)", ("1" if fts else "0",))

        count = 0
        for jsonl in sorted(pagetext_dir(root).glob("*.jsonl")):
            source_id = jsonl.stem
            for page in load_pagetext(root, source_id):
                conn.execute(
                    "INSERT INTO pages (source_id, pdf_page, printed_page, text) VALUES (?,?,?,?)",
                    (source_id, page.pdf_page, page.printed_page, page.text),
                )
                count += 1
        conn.commit()
        return count
    finally:
        conn.close()


def _uses_fts(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT value FROM meta WHERE key='fts'").fetchone()
    return bool(row) and row[0] == "1"


def search(root: Path, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
    path = index_path(root)
    if not path.is_file():
        raise FileNotFoundError(path)
    conn = sqlite3.connect(path)
    try:
        if _uses_fts(conn):
            rows = conn.execute(
                "SELECT source_id, pdf_page, printed_page, "
                "snippet(pages, 3, '[', ']', '…', 10) FROM pages "
                "WHERE pages MATCH ? LIMIT ?",
                (query, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT source_id, pdf_page, printed_page, substr(text,1,200) FROM pages "
                "WHERE text LIKE ? LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
        return [
            {"source_id": r[0], "pdf_page": r[1], "printed_page": r[2], "snippet": r[3]}
            for r in rows
        ]
    finally:
        conn.close()


def page(root: Path, source_id: str, pdf_page: int) -> str | None:
    path = index_path(root)
    if not path.is_file():
        raise FileNotFoundError(path)
    conn = sqlite3.connect(path)
    try:
        row = conn.execute(
            "SELECT text FROM pages WHERE source_id=? AND pdf_page=?",
            (source_id, pdf_page),
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()
