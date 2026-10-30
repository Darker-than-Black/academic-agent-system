"""DOI parsing and offline validation (02 §9.2, FR-36)."""

from __future__ import annotations

import re

_DOI = re.compile(r"^10\.\d{4,9}/\S+$")


def normalize_doi(raw: str) -> str:
    raw = raw.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:", "DOI:"):
        if raw.lower().startswith(prefix.lower()):
            raw = raw[len(prefix) :]
    return raw.strip()


def is_valid_doi(raw: str) -> bool:
    return bool(_DOI.match(normalize_doi(raw)))


def parse_doi_list(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]
