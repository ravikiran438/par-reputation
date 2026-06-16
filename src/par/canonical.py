"""Canonical JSON + content hashing for mandate tamper-evidence."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(obj: Any) -> str:
    """Deterministic JSON: sorted keys, no insignificant whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_hash(obj: Any) -> str:
    """sha256:<hex> over the canonical JSON of obj."""
    digest = hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
