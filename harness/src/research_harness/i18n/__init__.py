"""Message catalogs and lookup (02 §1.6).

User-facing strings live only in ``uk.yaml`` / ``en.yaml`` as flat dotted keys;
code refers to keys, never literals. A key missing from the requested language
falls back to the other language and logs a warning (also reported by
``rh-dev check``).
"""

from __future__ import annotations

import logging
import os
from functools import cache
from importlib.resources import files

import yaml

LANGS = ("uk", "en")
DEFAULT_LANG = "uk"
_FALLBACK_ORDER = {"uk": "en", "en": "uk"}

logger = logging.getLogger(__name__)


@cache
def _catalog(lang: str) -> dict[str, str]:
    data = files(__package__).joinpath(f"{lang}.yaml").read_text(encoding="utf-8")
    loaded = yaml.safe_load(data) or {}
    return {str(k): str(v) for k, v in loaded.items()}


def catalog_keys(lang: str) -> set[str]:
    """Keys defined in a language catalog (used by rh-dev check)."""
    return set(_catalog(lang).keys())


def resolve_lang(cli_lang: str | None = None, profile_lang: str | None = None) -> str:
    """Resolve the UI language: --lang → RH_LANG → profile → ``uk`` (02 §1.6)."""
    for candidate in (cli_lang, os.environ.get("RH_LANG"), profile_lang):
        if candidate in LANGS:
            return candidate  # type: ignore[return-value]
    return DEFAULT_LANG


def t(key: str, lang: str = DEFAULT_LANG, /, **params: object) -> str:
    """Look up ``key`` in ``lang`` (with fallback) and format with ``params``."""
    if lang not in LANGS:
        lang = DEFAULT_LANG
    template = _catalog(lang).get(key)
    if template is None:
        other = _FALLBACK_ORDER[lang]
        template = _catalog(other).get(key)
        if template is None:
            logger.warning("missing i18n key in all catalogs: %s", key)
            return key
        logger.warning("missing i18n key %r in %r; using %r", key, lang, other)
    try:
        return template.format(**params)
    except (KeyError, IndexError):
        return template
