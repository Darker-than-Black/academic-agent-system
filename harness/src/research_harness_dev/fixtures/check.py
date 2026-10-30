"""``rh-dev fixtures check <NAME>`` — validate a fixture's structure (M2-14).

Deterministic, spec-independent checks: composition per the card's §3.1, every
source carries a licence and a metadata hash, the injection PDF is synthetic and
labelled, no full text is committed, and refs.bib has the seeded duplicate and
malformed DOI. The annotation + manuscript span check is reported as pending
while the spec file ``05-eval-base.md`` is absent (it defines the format); it is
run once an ``annotation.yaml`` is present.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_HEX64 = re.compile(r"^[a-f0-9]{64}$")


def check_f4w(fixture_dir: Path) -> list[str]:
    problems: list[str] = []
    src_path = fixture_dir / "sources.yaml"
    if not src_path.is_file():
        return [f"missing {src_path}"]
    doc = yaml.safe_load(src_path.read_text(encoding="utf-8"))
    sources = doc.get("sources", [])

    uk = sum(1 for s in sources if s.get("lang") == "uk")
    en = sum(1 for s in sources if s.get("lang") == "en")
    abstract = sum(1 for s in sources if s.get("access") == "abstract")
    doubtful = sum(1 for s in sources if s.get("venue_quality") == "doubtful")
    injection = [s for s in sources if s.get("injection")]
    if uk != 6 or en != 6:
        problems.append(f"composition: expected 6 uk + 6 en, got {uk} uk + {en} en (§3.1)")
    if abstract != 2:
        problems.append(f"composition: expected 2 abstract-only, got {abstract} (§3.1)")
    if doubtful != 1:
        problems.append(f"composition: expected 1 doubtful venue, got {doubtful} (§3.1)")
    if len(injection) != 1:
        problems.append(f"composition: expected 1 injection source, got {len(injection)} (§3.1)")

    for s in sources:
        sid = s.get("id", "?")
        if not s.get("license"):
            problems.append(f"{sid}: no licence")
        if not _HEX64.match(str(s.get("metadata_sha256", ""))):
            problems.append(f"{sid}: metadata_sha256 missing or not 64-hex")
        if not s.get("locator"):
            problems.append(f"{sid}: no locator")

    # Injection PDF: synthetic, labelled, present, hashed.
    for s in injection:
        if not s.get("synthetic"):
            problems.append(f"{s['id']}: injection source must be marked synthetic (H6)")
        loc = str(s.get("locator", ""))
        pdf = fixture_dir / loc.removeprefix("file:") if loc.startswith("file:") else None
        if pdf is None or not pdf.is_file():
            problems.append(f"{s['id']}: injection PDF missing at {loc}")
        else:
            raw = pdf.read_bytes()
            if b"SYNTHETIC" not in raw:
                problems.append(f"{s['id']}: injection PDF not labelled SYNTHETIC")
            if not _HEX64.match(str(s.get("file_sha256", ""))):
                problems.append(f"{s['id']}: injection PDF has no file_sha256")

    # No committed full texts (H8).
    for f in fixture_dir.rglob("*.full.pdf"):
        problems.append(f"full text committed (H8): {f.relative_to(fixture_dir)}")
    if (fixture_dir / "fulltext").is_dir():
        for f in (fixture_dir / "fulltext").iterdir():
            problems.append(f"full text committed (H8): {f.relative_to(fixture_dir)}")

    problems += _check_bibtex(fixture_dir / "refs.bib")

    problems += _check_annotation(fixture_dir)
    return problems


def _paragraphs(text: str) -> list[str]:
    body = re.sub(r"(?s)^---.*?---\n", "", text, count=1)  # strip front matter
    body = re.sub(r"(?m)^#.*$", "", body)  # drop headings
    return [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]


def _check_annotation(fixture_dir: Path) -> list[str]:
    import yaml

    from research_harness.schemas import validate

    ann = fixture_dir / "annotation.yaml"
    if not ann.is_file():
        return [
            "PENDING (not a failure): annotation.yaml absent — author writes the reference "
            "annotation (§5.1)"
        ]
    doc = yaml.safe_load(ann.read_text(encoding="utf-8"))
    errors = validate("annotation", doc)
    if errors:
        return [f"annotation.yaml: schema invalid: {errors[0]}"]

    man = fixture_dir / "manuscript.md"
    if not man.is_file():
        return ["PENDING (not a failure): manuscript.md absent — spans cannot be resolved yet"]
    paras = _paragraphs(man.read_text(encoding="utf-8"))

    out: list[str] = []
    for claim in doc["claims"]:
        span = claim["span"]
        idx = span["paragraph"]
        cid = claim["claim_id"]
        if idx >= len(paras):
            out.append(f"{cid}: span paragraph {idx} out of range ({len(paras)} paragraphs)")
            continue
        if not (0 <= span["start"] < span["end"] <= len(paras[idx])):
            out.append(f"{cid}: span [{span['start']},{span['end']}] does not fit its paragraph")
    return out


def _check_bibtex(path: Path) -> list[str]:
    if not path.is_file():
        return [f"missing {path}"]
    text = path.read_text(encoding="utf-8")
    titles = re.findall(r"title\s*=\s*\{([^}]*)\}", text)
    has_dup = len(titles) != len(set(titles))
    dois = re.findall(r"doi\s*=\s*\{([^}]*)\}", text)
    has_bad_doi = any(not d.startswith("10.") for d in dois)
    out = []
    if not has_dup:
        out.append("refs.bib: no duplicate entry (one is required)")
    if not has_bad_doi:
        out.append("refs.bib: no malformed DOI (one is required)")
    return out


def main(name: str, fixture_dir: Path) -> int:
    if name != "F4-W":
        print(f"no checker for fixture {name!r}")
        return 2
    problems = check_f4w(fixture_dir)
    hard = [p for p in problems if not p.startswith("PENDING")]
    for p in problems:
        print(("note: " if p.startswith("PENDING") else "FAIL: ") + p)
    if hard:
        return 1
    print(f"fixtures check {name}: OK")
    return 0
