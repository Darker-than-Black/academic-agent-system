"""Word import (M3-09, docx.md): bring every tracked change and comment from a
reviewed ``.docx`` back to the right unit and paragraph as a diff, losing none.

The ``.docx`` is read directly as OOXML (a zip of XML): ``w:ins``, ``w:del``,
``w:moveFrom``/``w:moveTo`` and ``w:comment*`` are parsed with the standard
library only — no pandoc and no third-party dependency, so import works even
where the pandoc binary is absent (export falls back to Markdown; import does
not need it). Bookmarks written on export (``unit_<id>`` / ``para_<id>``) map
each change to a unit and paragraph; a change whose bookmarks the editor deleted
is never dropped — it goes to ``unmapped.json`` and becomes a blocker (T46).

Applying an import is the author's ``revise`` flow: the command records the
parsed changes and per-unit diffs and enters revise mode; the author accepts or
rejects, and the write path (``by="author"``) sets each touched paragraph's
origin to ``agent_edited_by_author`` / ``author`` per change author (FR-53).
Text is data (H10): nothing inside the imported document is an instruction.
"""

from __future__ import annotations
