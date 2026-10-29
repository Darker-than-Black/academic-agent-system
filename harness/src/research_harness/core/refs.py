"""Artifact references (02 §1.4): ``<kind>:<id>[/<part>][@<version>]``.

A reference names an artifact independently of its path, so renames do not
break links. ``file:<relative-path>`` is the last-resort form for an unmanaged
file and carries a validated relative path instead of an id.
"""

from __future__ import annotations

from dataclasses import dataclass

from research_harness.core.paths import validate_relative_path


@dataclass(frozen=True)
class Ref:
    kind: str
    id: str
    part: str | None = None
    version: str | None = None

    def format(self) -> str:
        if self.kind == "file":
            return f"file:{self.id}"
        out = f"{self.kind}:{self.id}"
        if self.part:
            out += f"/{self.part}"
        if self.version:
            out += f"@{self.version}"
        return out

    def __str__(self) -> str:
        return self.format()


def parse_ref(text: str) -> Ref:
    """Parse a reference string into a :class:`Ref`."""
    kind, sep, rest = text.partition(":")
    if not sep or not kind or not rest:
        raise ValueError(f"invalid ref (expected '<kind>:<id>'): {text!r}")

    if kind == "file":
        return Ref("file", validate_relative_path(rest))

    version: str | None = None
    if "@" in rest:
        rest, _, version = rest.rpartition("@")
        if not version:
            raise ValueError(f"empty version in ref: {text!r}")

    id_, _, part = rest.partition("/")
    if not id_:
        raise ValueError(f"missing id in ref: {text!r}")
    return Ref(kind, id_, part or None, version)


def format_ref(ref: Ref) -> str:
    return ref.format()
