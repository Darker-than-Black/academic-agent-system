"""P1-2: ДСТУ 8302:2015 CSL rendering harness.

No maintained ДСТУ 8302:2015 style exists in the official CSL repository
(citation-style-language/styles, checked 2026-11-02); the shipped .csl is an
in-house clean-room draft. This harness renders the draft against the author's
real reference examples and checks each one, but it NEVER invents references
(H6): with no author-supplied examples it skips with a clear message (the F5h
pattern). It is the scaffold the author fills once they commission/validate the
style.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from research_harness.export_docx import pandoc

_CSL = (
    Path(__file__).resolve().parents[2] / "rulepacks" / "ua-fahove-b" / "csl" / "dstu-8302-2015.csl"
)
_EXAMPLES = _CSL.parent / "examples"
_MIN = 10


def _load_examples() -> tuple[Path, list[dict]] | None:
    bib = _EXAMPLES / "references.bib"
    expected = _EXAMPLES / "expected.jsonl"
    if not (bib.is_file() and expected.is_file()):
        return None
    cases = [
        json.loads(line)
        for line in expected.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return bib, cases


@pytest.mark.skipif(not pandoc.have_pandoc(), reason="pandoc is not installed")
def test_dstu_csl_renders_real_examples(tmp_path: Path) -> None:
    loaded = _load_examples()
    if loaded is None:
        pytest.skip(
            "no author-supplied reference examples in "
            "rulepacks/ua-fahove-b/csl/examples/ (references.bib + expected.jsonl); "
            "the harness never invents references (H6)"
        )
    bib, cases = loaded
    assert len(cases) >= _MIN, f"need >= {_MIN} real reference examples, got {len(cases)}"

    md = tmp_path / "doc.md"
    md.write_text("---\nnocite: |\n  @*\n---\n", encoding="utf-8")
    out = tmp_path / "refs.txt"
    cmd = [
        "pandoc",
        str(md),
        "-o",
        str(out),
        "--from",
        "markdown",
        "--to",
        "plain",
        "--citeproc",
        "--bibliography",
        str(bib),
        "--csl",
        str(_CSL),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    rendered = out.read_text(encoding="utf-8")
    for case in cases:
        for needle in case.get("contains", []):
            assert needle in rendered, f"{case.get('key')}: expected {needle!r} in rendered refs"
