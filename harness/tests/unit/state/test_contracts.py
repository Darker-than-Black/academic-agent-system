"""StageContract tests (02 §5.7, ADP-002)."""

from __future__ import annotations

import dataclasses

import pytest

from research_harness.state.contracts import StageContract


def test_construct_defaults() -> None:
    c = StageContract(stage="A0")
    assert c.inputs == () and c.outputs == () and c.max_retries == 1 and c.gate is None


def test_full_contract() -> None:
    c = StageContract(
        stage="A4",
        inputs=("object:X/intake",),
        outputs=("object:X/protocol",),
        dod=("protocol.present",),
        gate="G1",
        error_codes=("E_PROTOCOL",),
        max_retries=0,
    )
    assert c.gate == "G1"
    assert c.dod == ("protocol.present",)


def test_frozen() -> None:
    c = StageContract(stage="A0")
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.stage = "A1"  # type: ignore[misc]
