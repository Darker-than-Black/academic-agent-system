"""F4-W metadata: synthetic BibTeX with Cyrillic authors, one duplicate and one
malformed DOI (M1-09, T38). Synthetic (H6); real F4-W sources are not needed."""

from __future__ import annotations

from pathlib import Path

BIBTEX = """@article{shevchenko2024,
  title = {Синтетичні дані у суспільних науках},
  author = {Шевченко, Тарас and Українка, Леся},
  year = {2024},
  doi = {10.1234/synthetic.2024},
  url = {https://example.org/a}
}

@article{shevchenko2024preprint,
  title = {Синтетичні дані у суспільних науках},
  author = {Шевченко, Тарас and Українка, Леся},
  year = {2023},
  doi = {10.1234/synthetic.2024}
}

@article{broken2024,
  title = {Робота з поганим DOI},
  author = {Франко, Іван},
  year = {2024},
  doi = {not-a-doi/123}
}
"""


def build_f4w_metadata(dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    bib = dest / "refs.bib"
    bib.write_text(BIBTEX, encoding="utf-8")
    return dest
