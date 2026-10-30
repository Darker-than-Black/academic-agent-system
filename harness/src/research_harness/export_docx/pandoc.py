"""Thin pandoc wrapper (external binary, 01 §3). No live calls; pure local
conversion. Callers check ``have_pandoc()`` and fall back to Markdown export.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from research_harness.core.errors import ToolFailureError


def have_pandoc() -> bool:
    return shutil.which("pandoc") is not None


def to_docx(
    md_path: Path,
    out_path: Path,
    *,
    reference_docx: Path | None = None,
    csl: Path | None = None,
    bib: Path | None = None,
) -> Path:
    if not have_pandoc():
        raise ToolFailureError("error.pandoc_missing")
    cmd = ["pandoc", str(md_path), "-o", str(out_path), "--from", "markdown", "--to", "docx"]
    if reference_docx and reference_docx.is_file():
        cmd += ["--reference-doc", str(reference_docx)]
    if bib and bib.is_file():
        cmd += ["--citeproc", "--bibliography", str(bib)]
        if csl and csl.is_file():
            cmd += ["--csl", str(csl)]
    result = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603
    if result.returncode != 0:
        raise ToolFailureError("error.pandoc_failed")
    return out_path
