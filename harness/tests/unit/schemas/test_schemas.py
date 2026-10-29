"""Schema inventory tests (02 §14): meta-schema validity + example behaviour."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from research_harness import schemas

EXAMPLES = Path(__file__).parent / "examples"
EXAMPLE_DIRS = sorted(p.name for p in EXAMPLES.iterdir() if p.is_dir())


def test_all_schemas_meta_valid() -> None:
    for name in schemas.schema_names():
        Draft202012Validator.check_schema(schemas.load_schema(name))


def test_every_m1_schema_has_examples() -> None:
    # common.schema.json holds only $defs and has no instances.
    expected = {n for n in schemas.schema_names() if n != "common"}
    assert set(EXAMPLE_DIRS) == expected


@pytest.mark.parametrize("name", EXAMPLE_DIRS)
def test_valid_examples_pass(name: str) -> None:
    valids = sorted((EXAMPLES / name).glob("valid-*.json"))
    assert valids, f"{name} has no valid example"
    for path in valids:
        errors = schemas.validate(name, json.loads(path.read_text(encoding="utf-8")))
        assert errors == [], f"{path.name} should pass {name}: {errors}"


@pytest.mark.parametrize("name", EXAMPLE_DIRS)
def test_invalid_examples_fail(name: str) -> None:
    invalids = sorted((EXAMPLES / name).glob("invalid-*.json"))
    assert len(invalids) >= 2, f"{name} needs >=2 invalid examples, has {len(invalids)}"
    for path in invalids:
        errors = schemas.validate(name, json.loads(path.read_text(encoding="utf-8")))
        assert errors, f"{path.name} should fail {name} but validated clean"


def test_claim_supported_requires_evidence_and_dependencies() -> None:
    base = json.loads((EXAMPLES / "claim" / "valid-1.json").read_text(encoding="utf-8"))
    base["support"] = "supported"  # empty evidence + dependencies
    assert schemas.validate("claim", base)


def test_claim_own_numeric_requires_tuple_and_result_ref() -> None:
    base = json.loads((EXAMPLES / "claim" / "valid-1.json").read_text(encoding="utf-8"))
    base["kind"] = "own_numeric"
    assert schemas.validate("claim", base)


def test_result_row_without_unit_fails() -> None:
    row = json.loads((EXAMPLES / "result-row" / "valid-1.json").read_text(encoding="utf-8"))
    row.pop("unit")
    assert schemas.validate("result-row", row)


def test_loader_unknown_schema_raises() -> None:
    with pytest.raises(KeyError):
        schemas.load_schema("does-not-exist")
