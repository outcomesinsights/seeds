---
id: seeds-cb6r
title: "BUG: 'seeds answer' silently destroys a prior answer — the guard that 'update --content' has was never given to 'answer'"
status: resolved
type: concern
created_at: 2026-08-26T18:02:05.442796+00:00
updated_at: 2026-08-31T20:02:48.005975+00:00
resolved_at: 2026-08-26T19:38:40.125221+00:00
resolution: "Fixed in daf5e2a (bead seeds-btr): answer refuses a re-answer by default, --replace discards, --append revises, reusing _guard_content_replacement. resolved_at re-stamps on every successful path. Efficacy: minor tweaking, PLANNING MISS — the bead said reuse the shared helper without noticing the helper carried caller-specific prose, which produced seeds-3dkj. Better bead: before reusing a shared helper, check whether any of its OUTPUT is caller-specific."
tags:
  - bug
  - answer
  - data-loss
  - guard
  - consistency
  - questions
  - peer-report
  - 2026-08-26
relationships:
  - target_id: seeds-faxd
    rel_type: relates-to
    created_at: 2026-08-26T18:02:31.415813+00:00
  - target_id: seeds-3dkj
    rel_type: relates-to
    created_at: 2026-08-26T19:28:50.726074+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Reported by a peer session in the home-manager repo, 2026-08-26, and confirmed in code here.

WHAT HAPPENS. Answering an already-answered question overwrites the previous answer with no warning and no way to recover it from the tool. The reporter answered hm-ml5, then answered it again to record a reversal of the decision; the first answer was destroyed in the database. Because the committed JSONL still held the original, the database and disk then silently diverged — which is how it was noticed at all.

CONFIRMED IN CODE. cli.py:1090-1098:
    question_seed = db.get_seed(question_id)
    ...
    question_seed.content = answer_text
    question_seed.status = SeedStatus.RESOLVED
    question_seed.resolved_at = now_utc()
    db.update_seed(question_seed)
The assignment is unconditional. Nothing checks whether the seed already has content, and nothing checks whether it is already RESOLVED — so re-answering a resolved question is indistinguishable from answering an open one.

THE INCONSISTENCY IS THE POINT. `seeds update` already has exactly this guard and its help text is explicit: "--content replaces the body wholesale, so it is refused on a seed that has been edited since it was created; use --append to add to the deliberation, or --replace to discard it deliberately." That reasoning applies verbatim to an answer — arguably more strongly, since an answer is a recorded conclusion rather than a working draft. The verb `answer` simply never got the guard.

IT HAS BITTEN THE SAME REPO TWICE. The reporter cites commit a576141 there, "fix(seeds): restore the hm-57i answer a second `seeds answer` overwrote," and today's incident is the second. I have not read that repo, so the commit is their evidence rather than mine — but the mechanism is confirmed above and makes the recurrence entirely predictable.

DESIGN QUESTION TO SETTLE BEFORE BUILDING — what should a second `answer` do? An answer being revised is a normal and valuable event; a reversal is exactly the kind of thing this tool exists to capture. So refusing outright is not obviously right.
  a) Refuse, mirroring `update --content`, and require an explicit flag to overwrite. Consistent, minimal, and it stops the data loss. But it makes recording a reversal awkward.
  b) Append by default, so a re-answer becomes a dated revision below the original and the question reads chronologically. This matches what the reporter actually wanted and what they had to reconstruct by hand — and it matches how seed bodies already evolve.
  c) Refuse by default, with `--replace` to discard deliberately and `--append` to revise. Most consistent with the verb family that already exists, at the cost of one more flag.

My read is (c): the guard stops the silent loss, and `--append` makes recording a reversal a first-class action rather than a workaround. Whichever is chosen, the failure being prevented is silent destruction of a recorded conclusion, so the default must not be overwrite.

RELATED SURFACE worth checking in the same pass: any other verb that assigns to `content` unconditionally. `answer` was missed once already; a grep for direct content assignment would show whether it is alone.


--- THE FIX IS SMALLER THAN EXPECTED (verified 2026-08-26) ---

The guard is already a reusable helper, not logic inlined in `update`. cli.py:1003-1004:
    if content is not None and not replace:
        _guard_content_replacement(seed)

So giving `answer` the same protection is a call to an existing function, exactly as the reporter guessed. The design question above (refuse / append / both) is the only real work; the mechanism is already built and tested.

RELATED-SURFACE SWEEP, done. `grep -n "\.content = " src/seeds/*.py` returns exactly three sites:
- cli.py:1013 — `update --content`, guarded at 1003-1004
- cli.py:1017 — `update --append`, safe by construction (it concatenates onto the existing body)
- cli.py:1095 — `answer`, unguarded

So `answer` is the only unprotected writer of a seed body. Nothing else is hiding.


--- DECISION (@aguynamedryan, 2026-08-26) ---

Option (c): refuse by default, with `--replace` to discard the old answer deliberately and `--append` to record a revision.

This mirrors `update --content` exactly and reuses `_guard_content_replacement` rather than inventing a second guard. The reasoning that settled it: an answer is a recorded conclusion, so the default must never destroy one silently; and a reversal is a first-class event this tool exists to capture, so revising needs its own verb rather than a hand-concatenation workaround.

Scope now closed. Ready to build.


--- SHIPPED (2026-08-26, commit daf5e2a, bead seeds-btr) ---

Option (c) built as ruled: refuse by default, `--replace` to discard, `--append` to revise, reusing `_guard_content_replacement`. 7 tests, suite 572 -> 579.

THREE DECISIONS MADE IN IMPLEMENTATION that this deliberation had left open or had not anticipated:

1. `--append` and `--replace` are BOOLEAN flags, not value-taking options like `update`'s `-a`. The reason is a shape difference this seed missed: `answer` already takes the answer text as a positional argument, so that one argument serves as the new answer, the replacement, or the text to append. A second value-bearing option would have been redundant. `update` has no positional body argument, which is why its `-a` takes a value — so "mirror update's flags" was not quite the right instruction.

2. Passing both flags together is refused as contradictory (exit 1, content untouched). Not in the deliberation at all; `update` has no direct analogue because its `-a` and `-c` are value options rather than a flag pair. A small, correct addition.

3. resolved_at, which this seed explicitly flagged as needing a deliberate call: EVERY successful path re-stamps it to now -- first answer, `--replace`, and `--append` alike. The reasoning is that a revision is itself a resolution event, so the field marks the moment of the LATEST resolution rather than the first. Pinned by `test_append_re_stamps_resolved_at`.

EFFICACY. Tweaking needed: minor -- and it was a genuine PLANNING MISS, not an inherent unknown.

The bead said "reuse `_guard_content_replacement` rather than inventing a second guard," which was right and remains right. What it failed to notice is that the helper carried caller-SPECIFIC user-facing prose: its refusal names `--content` and tells the user to run `seeds update`. So the moment `answer` reused it, a guarded re-answer began advising a flag `answer` does not have. The implementing agent spotted it, correctly declined to widen its own scope, and reported it -- which is how it became seeds-3dkj and then a same-day fix.

What a better bead would have said: before reusing a shared helper, check whether any of its OUTPUT is specific to its current caller. Sharing a decision is safe; sharing prose is not.
