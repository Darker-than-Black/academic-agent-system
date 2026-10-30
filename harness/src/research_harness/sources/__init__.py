"""Sources: registry, metadata adapters, import, dedup, existence, retractions.

Milestone M2 (card M2-01). The core stays SDK-free (H5): adapters perform HTTP
through an injected transport so tests run on recorded fixtures with no live
calls, and no paid API is ever contacted (H9).
"""
