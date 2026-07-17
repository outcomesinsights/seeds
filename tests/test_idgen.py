"""Tests for base36 hash-ID generation (see seeds-199)."""

from seeds.idgen import (
    collision_probability,
    compute_adaptive_length,
    encode_base36,
    generate_hash_id,
)


class TestEncodeBase36:
    """Tests for encode_base36."""

    def test_pads_short_values(self):
        """Verify short values are left-padded with '0' to reach length."""
        assert encode_base36(b"\x00\x00\x01", 5) == "00001"

    def test_zero_value_pads_to_zeros(self):
        """Verify an all-zero input encodes to a zero-filled string."""
        assert encode_base36(b"\x00\x00", 4) == "0000"

    def test_exact_length_returns_unpadded(self):
        """Verify a value whose base36 form is exactly `length` is untouched."""
        assert encode_base36(bytes([1, 0]), 2) == "74"  # 256 decimal -> "74"

    def test_truncates_to_least_significant_digits(self):
        """Verify values longer than `length` keep the least-significant digits."""
        # 4294967295 decimal is a 7-digit base36 number, so requesting fewer
        # digits must truncate from the left (keep the tail).
        full = encode_base36(b"\xff\xff\xff\xff", 20).lstrip("0")
        assert len(full) == 7
        truncated = encode_base36(b"\xff\xff\xff\xff", 4)
        assert truncated == full[-4:]


class TestGenerateHashId:
    """Tests for generate_hash_id."""

    def test_format_prefix_and_length(self):
        """Verify the result is '<prefix>-' followed by `length` chars."""
        result = generate_hash_id("seeds", "hello", 1000, 0, 4)
        assert result.startswith("seeds-")
        assert len(result) == len("seeds-") + 4

    def test_suffix_uses_base36_alphabet(self):
        """Verify the suffix only contains base36 (0-9a-z) characters."""
        result = generate_hash_id("seeds", "hello", 1000, 0, 8)
        suffix = result.split("-", 1)[1]
        assert all(c in "0123456789abcdefghijklmnopqrstuvwxyz" for c in suffix)

    def test_bumping_nonce_changes_suffix(self):
        """Verify bumping the nonce changes the generated suffix."""
        a = generate_hash_id("seeds", "hello", 1000, 0, 6)
        b = generate_hash_id("seeds", "hello", 1000, 1, 6)
        assert a != b

    def test_deterministic_for_same_inputs(self):
        """Verify identical inputs produce identical output."""
        a = generate_hash_id("seeds", "hello", 1000, 0, 6)
        b = generate_hash_id("seeds", "hello", 1000, 0, 6)
        assert a == b


class TestCollisionProbability:
    """Tests for collision_probability."""

    def test_zero_items_has_zero_probability(self):
        """Verify no items means no collision risk."""
        assert collision_probability(0, 4) == 0.0

    def test_increases_with_more_items(self):
        """Verify probability grows monotonically with item count."""
        low = collision_probability(10, 4)
        high = collision_probability(1000, 4)
        assert high > low

    def test_decreases_with_longer_length(self):
        """Verify probability shrinks monotonically with hash length."""
        short = collision_probability(1000, 3)
        long = collision_probability(1000, 6)
        assert long < short


class TestComputeAdaptiveLength:
    """Tests for compute_adaptive_length threshold behavior (beads' table)."""

    def test_zero_items_returns_min_length(self):
        assert compute_adaptive_length(0) == 3

    def test_160_items_returns_min_length(self):
        assert compute_adaptive_length(160) == 3

    def test_200_items_bumps_to_four(self):
        assert compute_adaptive_length(200) == 4

    def test_1000_items_bumps_to_five(self):
        assert compute_adaptive_length(1000) == 5
