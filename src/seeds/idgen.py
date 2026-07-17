"""Beads-style base36 hash IDs with adaptive length. See seeds-199."""

from __future__ import annotations

import hashlib
import math

BASE36_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"

# Defaults (beads DefaultAdaptiveConfig). Overridable via the seeds config table.
DEFAULT_MAX_COLLISION_PROB = 0.25
DEFAULT_MIN_HASH_LENGTH = 3
DEFAULT_MAX_HASH_LENGTH = 8

# SHA-256 bytes fed to the encoder per target length (beads).
_NUM_BYTES = {3: 2, 4: 3, 5: 4, 6: 4, 7: 5, 8: 5}


def encode_base36(data: bytes, length: int) -> str:
    """Encode bytes as base36 of exactly `length` chars: left-pad with '0';
    if longer, keep the least-significant digits (matches beads EncodeBase36)."""
    num = int.from_bytes(data, "big")
    chars: list[str] = []
    while num > 0:
        num, rem = divmod(num, 36)
        chars.append(BASE36_ALPHABET[rem])
    s = "".join(reversed(chars)) or "0"
    if len(s) < length:
        s = "0" * (length - len(s)) + s
    if len(s) > length:
        s = s[len(s) - length :]
    return s


def generate_hash_id(
    prefix: str, seed_text: str, timestamp_ns: int, nonce: int, length: int
) -> str:
    """Return '<prefix>-<base36 hash>' of the given length. The ns timestamp +
    nonce make it effectively unique; the caller bumps nonce to resolve a DB
    collision (matches beads GenerateHashID)."""
    payload = f"{seed_text}|{timestamp_ns}|{nonce}"
    digest = hashlib.sha256(payload.encode()).digest()
    num_bytes = _NUM_BYTES.get(length, 3)
    return f"{prefix}-{encode_base36(digest[:num_bytes], length)}"


def collision_probability(num_items: int, length: int) -> float:
    """Birthday-paradox P(collision) ≈ 1 - e^(-n²/2N), N = 36**length."""
    total = 36.0**length
    return 1.0 - math.exp(-float(num_items * num_items) / (2.0 * total))


def compute_adaptive_length(
    num_items: int,
    min_length: int = DEFAULT_MIN_HASH_LENGTH,
    max_length: int = DEFAULT_MAX_HASH_LENGTH,
    max_prob: float = DEFAULT_MAX_COLLISION_PROB,
) -> int:
    """Smallest length in [min,max] with collision prob <= max_prob; returns
    max_length if none qualifies (matches beads computeAdaptiveLength)."""
    for length in range(min_length, max_length + 1):
        if collision_probability(num_items, length) <= max_prob:
            return length
    return max_length
