"""Tests for Database.next_id() base36 hash-ID minting (see seeds-199, seeds-mlj).

Uses the shared ``db`` fixture from conftest.py (an initialized Database in an
isolated ``temp_dir``) — never the real project .seeds/ store.
"""

import re

from seeds.models import Seed

HASH_ID_RE = re.compile(r"^seeds-[0-9a-z]{3,8}$")


class TestNextIdHashFormat:
    """New top-level IDs are beads-style base36 hashes, not sequential."""

    def test_new_top_level_id_is_hash_not_sequential(self, db):
        """Freshly minted IDs have the hash shape, and none is a counter value.

        Digit-ness is deliberately not the test: an all-digit suffix like
        '060' is a perfectly ordinary base36 hash (seeds-skc), so asserting a
        minted ID isn't purely numeric only samples the randomness — it fails
        ~3% of the time per ID and says nothing when it passes (seeds-oaw).
        What separates the schemes deterministically is width: a sequential
        minter against an empty store hands out 'seeds-1'..'seeds-20', while
        every hash suffix is at least three base36 characters wide.
        """
        ids = [db.next_id(seed_text=f"thought {i}") for i in range(20)]
        for seed_id in ids:
            assert HASH_ID_RE.match(seed_id), seed_id
        sequential = {f"seeds-{i}" for i in range(1, len(ids) + 1)}
        assert not sequential & set(ids), sorted(sequential & set(ids))

    def test_two_rapid_creates_differ(self, db):
        """Back-to-back creates (no delay) mint distinct IDs."""
        id1 = db.next_id(seed_text="thought")
        db.create_seed(Seed(id=id1, title="thought"))
        id2 = db.next_id(seed_text="thought")
        assert id1 != id2


class TestNextIdChildren:
    """Children of hash-ID parents still use the parent.N scheme untouched."""

    def test_child_of_hash_id_parent(self, db):
        parent_id = db.next_id(seed_text="parent thought")
        db.create_seed(Seed(id=parent_id, title="parent thought"))

        child_id = db.get_next_child_id(parent_id)
        assert child_id == f"{parent_id}.1"


class TestNextIdGrandfathering:
    """Existing sequential IDs are never renumbered or reissued."""

    def test_preexisting_sequential_id_never_reissued(self, db):
        db.create_seed(Seed(id="seeds-5", title="Legacy sequential"))

        for _ in range(20):
            candidate = db.next_id(seed_text="probe")
            assert candidate != "seeds-5"

        # Grandfathered row itself is untouched.
        assert db.get_seed("seeds-5").title == "Legacy sequential"


class TestNextIdAdaptiveLength:
    """Suffix length scales with the top-level seed count (seeds-199)."""

    def test_200_top_level_seeds_yields_four_char_suffix(self, db):
        for i in range(1, 201):
            db.create_seed(Seed(id=f"seeds-{i}", title=f"Seed {i}"))

        new_id = db.next_id(seed_text="the 201st")
        assert HASH_ID_RE.match(new_id)
        suffix = new_id.split("-", 1)[1]
        assert len(suffix) == 4

        # get_next_child_id is untouched by the adaptive length change.
        db.create_seed(Seed(id=new_id, title="the 201st"))
        assert db.get_next_child_id(new_id) == f"{new_id}.1"
