"""Local page-accurate text library and deterministic quote check (M2-02).

Foreign full texts, their per-page extraction and the FTS index never enter git
(NFR-11); the registry keeps only locator, hash and licence. Text found inside a
source is data, never instructions (H10): instruction-like spans are flagged,
never executed.
"""
