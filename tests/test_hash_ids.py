"""Tests for Store.next_id() base36 hash-ID minting (see seeds-199, seeds-mlj).

Uses the shared ``store`` fixture from conftest.py (an initialized seed-file
store in an isolated ``temp_dir``) — never the real project .seeds/ store.
"""

import re

from seeds.store import new_record

HASH_ID_RE = re.compile(r"^seeds-[0-9a-z]{3,8}$")


class TestNextIdHashFormat:
    """New top-level IDs are beads-style base36 hashes, not sequential."""

    def test_new_top_level_id_is_hash_not_sequential(self, store):
        """Freshly minted IDs have the hash shape, and none is a counter value.

        Digit-ness is deliberately not the test: an all-digit suffix like
        '060' is a perfectly ordinary base36 hash (seeds-skc), so asserting a
        minted ID isn't purely numeric only samples the randomness — it fails
        ~3% of the time per ID and says nothing when it passes (seeds-oaw).
        What separates the schemes deterministically is width: a sequential
        minter against an empty store hands out 'seeds-1'..'seeds-20', while
        every hash suffix is at least three base36 characters wide.
        """
        ids = [store.next_id(seed_text=f"thought {i}") for i in range(20)]
        for seed_id in ids:
            assert HASH_ID_RE.match(seed_id), seed_id
        sequential = {f"seeds-{i}" for i in range(1, len(ids) + 1)}
        assert not sequential & set(ids), sorted(sequential & set(ids))

    def test_two_rapid_creates_differ(self, store):
        """Back-to-back creates (no delay) mint distinct IDs."""
        id1 = store.next_id(seed_text="thought")
        store.create(new_record(id1, "thought"))
        id2 = store.next_id(seed_text="thought")
        assert id1 != id2


class TestNextIdChildren:
    """Children of hash-ID parents still use the parent.N scheme untouched."""

    def test_child_of_hash_id_parent(self, store):
        parent_id = store.next_id(seed_text="parent thought")
        store.create(new_record(parent_id, "parent thought"))

        child_id = store.next_child_id(parent_id)
        assert child_id == f"{parent_id}.1"


class TestNextIdGrandfathering:
    """Existing sequential IDs are never renumbered or reissued."""

    def test_preexisting_sequential_id_never_reissued(self, store):
        store.create(new_record("seeds-5", "Legacy sequential"))

        for _ in range(20):
            candidate = store.next_id(seed_text="probe")
            assert candidate != "seeds-5"

        # Grandfathered row itself is untouched.
        assert store.get("seeds-5").title == "Legacy sequential"


class TestNextIdAdaptiveLength:
    """Suffix length scales with the top-level seed count (seeds-199)."""

    def test_200_top_level_seeds_yields_four_char_suffix(self, store):
        for i in range(1, 201):
            store.create(new_record(f"seeds-{i}", f"Seed {i}"))

        new_id = store.next_id(seed_text="the 201st")
        assert HASH_ID_RE.match(new_id)
        suffix = new_id.split("-", 1)[1]
        assert len(suffix) == 4

        # next_child_id is untouched by the adaptive length change.
        store.create(new_record(new_id, "the 201st"))
        assert store.next_child_id(new_id) == f"{new_id}.1"
