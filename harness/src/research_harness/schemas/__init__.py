"""JSON Schema loader (02 §14).

Schemas are shipped as package data and cross-reference each other by ``$id``
under ``https://rh.spec/schemas/``. The loader registers every schema in a
``referencing`` registry so Draft 2020-12 validators resolve those refs.
"""

from __future__ import annotations

import json
from functools import cache
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

BASE_URI = "https://rh.spec/schemas/"


@cache
def _schema_texts() -> dict[str, str]:
    out: dict[str, str] = {}
    for entry in files(__package__).iterdir():
        if entry.name.endswith(".schema.json"):
            out[entry.name] = entry.read_text(encoding="utf-8")
    return out


@cache
def load_schema(name: str) -> dict[str, Any]:
    """Load one schema by file name (with or without the ``.schema.json`` suffix)."""
    filename = name if name.endswith(".schema.json") else f"{name}.schema.json"
    texts = _schema_texts()
    if filename not in texts:
        raise KeyError(f"unknown schema: {name}")
    return json.loads(texts[filename])


def schema_names() -> list[str]:
    """Bare schema names (without the ``.schema.json`` suffix)."""
    return sorted(n[: -len(".schema.json")] for n in _schema_texts())


@cache
def _registry() -> Registry:
    resources = []
    for filename, text in _schema_texts().items():
        contents = json.loads(text)
        uri = contents.get("$id", BASE_URI + filename)
        resources.append((uri, Resource.from_contents(contents, default_specification=DRAFT202012)))
    return Registry().with_resources(resources)


@cache
def get_validator(name: str) -> Draft202012Validator:
    """Return a Draft 2020-12 validator for a schema, with cross-refs resolved."""
    return Draft202012Validator(load_schema(name), registry=_registry())


def validate(name: str, instance: Any) -> list[str]:
    """Validate ``instance`` against a schema; return a list of error messages."""
    validator = get_validator(name)
    return [
        f"{'/'.join(str(p) for p in err.path) or '<root>'}: {err.message}"
        for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    ]


def is_valid(name: str, instance: Any) -> bool:
    return not validate(name, instance)
