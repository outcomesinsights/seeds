---
id: seeds-tk5y
title: seeds update -c silently replaces deliberation content — one character from -a, no warning, no confirmation
status: resolved
type: concern
created_at: 2026-08-10T17:12:20.229263+00:00
updated_at: 2026-08-31T20:02:49.958567+00:00
resolved_at: 2026-08-11T19:45:49.925515+00:00
resolution: "Shipped in v0.5.0 across three beads: seeds-884 (`-c` guard), seeds-agk.1 (timestamp validation), seeds-agk.2 (divergence-aware export). seeds sync and seeds import now refuse to destroy deliberation rather than doing it silently.\n\nEFFICACY — tweaking needed: SIGNIFICANT. One planning-miss and one priority-miss.\n\nPLANNING-MISS. The locked design gated on 'updated_at == created_at means nothing has accumulated.' That invariant never held: Seed took two separate now_utc() readings ~8 microseconds apart, so every new seed already read as edited and -c would have refused on all of them. Making it work required changing the data model (updated_at mirrors created_at at construction) — beyond the bead's scope and necessary for the feature to function at all.\n  What a better bead would have said: before locking a design on a field invariant, VERIFY the invariant holds. One line of python would have caught it. I asserted a relationship between two fields without checking whether it was ever true.\n  Knock-on the design did not anticipate: 234 of 270 existing seeds carry that drift, so --replace is the ordinary path for pre-existing seeds, not the redaction emergency the design imagined.\n\nPRIORITY-MISS, discovered after shipping. Ryan asked whether the git history could show how often this actually bit. It can, and the answer is: never. Across 67 commits and 14,444 seed-version comparisons spanning 2026-02 to 2026-08 — zero content shrinkages, zero non-append losses. The single non-append change GREW 560->2513 chars with the old text fully contained; the 163 'vanished' seeds were all one commit, the seed- -> seeds- ID migration.\n  This is evidence of absence, not absence of evidence: the JSONL is git-tracked, so a clobber would leave a fingerprint, and there is none. The loss paths need two machines editing one seed between syncs; in practice this has been one person driving agents on one host.\n  So 0.5.0 was PREVENTIVE, not corrective. The mechanism was real and reproducible (a future-dated record ate a real append in testing), and the multi-machine scenario is the acknowledged direction — base36 IDs exist because two machines were already colliding. But P1 was a notch high for insurance against something that has not happened.\n  What a better bead would have said: measure historical exposure BEFORE assigning priority. The data was sitting in git the whole time and took one script to extract."
tags:
  - cli
  - safety
  - deliberation-integrity
  - data-loss
  - ux
relationships:
  - target_id: seeds-6hj5
    rel_type: relates-to
    created_at: 2026-08-10T17:12:45.160395+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

`seeds update` exposes two flags that differ by one character and by everything else:

```
-c, --content TEXT    New content (replaces existing)
-a, --append TEXT     Append to content
```

`-c` discards the entire existing body with **no warning, no confirmation prompt, no diff, no backup, no dry-run**. For a tool whose whole purpose is preserving how thinking developed, that is a sharp edge pointed at the thing being protected.

Surfaced 2026-08-10 when @aguynamedryan, on hearing the word "rewrite," asked whether that meant throwing out history. It didn't — every mutation this session used `-a` — but the question exposed that nothing in the tool would have stopped it.

## Why it matters more here than in a generic CRUD tool

A seed whose deliberation is replaced isn't a seed anymore, it's a note. The value is reading how the thinking *moved*, including the parts that turned out wrong. Concrete example from the same session: seeds-6hj5 originally argued the hash-ref problem was "irreducible — no regex can separate them." @aguynamedryan pushed back three times and drove out a workable design. That original wrong framing is worth keeping, because it shows the conclusion was earned rather than obvious. Overwrite it and the record reads as a tidy insight nobody had to argue for.

The failure mode is specifically an **agent** one. An agent reaching for `-c` when it meant `-a` destroys deliberation silently and reports success. Nothing distinguishes the two in the output.

## Mitigation that already exists (partial)

`.seeds/seeds.jsonl` is git-tracked, so a clobbered body is recoverable via `git log -p`. Real safety net — but it requires *knowing it happened*. Nothing surfaces the loss at the time, so the realistic discovery path is noticing a seed reads oddly weeks later.

## What actually justifies `-c` (@aguynamedryan's question: "what would be good scenarios?")

Worked through honestly, the list is short, and the legitimate cases share a shape:

1. **Redacting something that must not exist.** A credential, password, or client name arrived with a pasted body. Appending "ignore the above" does not remove it. This is the only case where deletion is the *requirement*, and no append-only design can serve it. Caveat: `-c` does not finish the job — the secret remains in git history, which needs separate scrubbing. It stops the bleeding, it is not the cure.
2. **A botched capture, seconds old.** Shell quoting ate half the content, a `$VAR` expanded, wrong paste buffer. No deliberation exists yet; the content is simply wrong.
3. **Encoding repair.** Literal `\n` in the body, mangled unicode. Same family as (2) — repairing a capture that never worked, not editing a thought.

**Explicitly NOT a justification — considered and rejected:** "restructuring a seed that has grown unwieldy." That is exactly the case with history worth keeping. If a seed has become unreadable, resolve it with a summary or split it; do not flatten the record.

## Proposed design — gate on whether deliberation exists, NOT on length

The legitimate cases are all either *nothing has accumulated yet* or *an emergency append cannot solve*. Both are detectable from fields the model already carries (`created_at`, `updated_at`; there is no revision count):

- **`updated_at == created_at`** — never been added to, so no deliberation exists -> `-c` just works, silently. Covers (2) and (3), the common cases.
- **Already updated** -> `-c` refuses, prints what it would discard (length + first line), and points at `-a`.
- **`--replace`** — explicit override for case (1), the redaction emergency.

An earlier suggestion of "warn when discarding more than N characters" was rejected: length is the wrong proxy. A 60-character seed refined over a week deserves more protection than a 4,000-character one pasted wrong ten seconds ago, and a character threshold gets that exactly backwards.

## Open questions

- Should the same guard apply to `--tags` (also "replaces existing") and `--title`? Tags and titles carry far less deliberation; probably not worth it, but the inconsistency should be deliberate rather than accidental.
- Does `seeds import` (last-write-wins upsert) have the same exposure — can a stale JSONL silently overwrite newer deliberation? Worth checking; different code path, same class of risk.
- Is there any case for a `--dry-run` on `update`, mirroring `rename-prefix --dry-run`?



---

## Promoted to beads (2026-08-10)

- **seeds-884** (P2, feature) — Guard `seeds update -c`: refuse to discard accumulated deliberation without `--replace`. Carries the locked `updated_at == created_at` gate and the explicit rejection of the character-count heuristic.
- **seeds-xrx** (P2, task) — Investigation: can `seeds import`'s last-write-wins upsert silently overwrite newer deliberation? Deliberately scoped to answering the question, not fixing it — the remedy is a design decision. Findings come back to this seed.

Both are bead IDs, not seed IDs.

Open question 1 (should `--tags` get the same guard?) and open question 3 (`update --dry-run`?) are NOT promoted — neither has been ruled on.



---

## Open questions 1 and 3 resolved (2026-08-10)

### Q1: should `--tags` get the same guard? **No.**

@aguynamedryan: *"I flag things sometimes for meetings, and then I'd like to unflag them after they've been handled."*

That settles it. Tags are **working state**, not deliberation. Wholesale replacement is the normal operation for them, not a destructive accident — the exact opposite of `--content`, where replacement is almost always a mistake. A guard would obstruct the primary use case. The inconsistency with `-c` is therefore deliberate and worth stating in the code: content accumulates and must be protected; tags churn by design.

**But the exchange surfaced a different gap.** `--tags` is full-replacement (`seed.tags = [...]` at cli.py:830) and there are no additive operations — no `--add-tag`, no `--remove-tag` (verified: zero matches in src/). So the flag/unflag cycle requires retyping every *other* tag each time. To add `meeting` to a seed tagged `nix, packaging, distribution, installation`, you must retype all five; to remove it later, all four. Forget one and it is silently dropped, with no warning — the same silent-loss shape as the `-c` problem, just cheaper to recover from.

The remedy is ergonomics, not a guard: `--add-tag` / `--remove-tag` alongside the existing wholesale `--tags`. Not promoted — this is an observation about a workflow @aguynamedryan described, not yet a confirmed pain.

### Q3: is there a case for `update --dry-run`? **No — retracted.**

This was raised by analogy to `rename-prefix --dry-run`, and the analogy does not hold.

`rename-prefix --dry-run` earns its keep because the operation has an **unpredictable blast radius**: it rewrites every seed ID and every body reference across the entire database, and you cannot know in advance what it will touch. Previewing is genuinely informative.

`seeds update` changes one named seed to a value you just typed. A dry run would show you the string you already have in your shell history. There is nothing to discover.

The one genuinely useful thing a dry run *could* have shown — what `-c` is about to discard — is delivered better by the guard bead itself, whose refusal message prints the discarded size and first line at exactly the moment it matters, without requiring anyone to remember to ask first.

## Open question 2 answered: the import path is NOT the sibling footgun — the export path is (2026-08-10, bead seeds-xrx)

This seed asked whether `seeds import`'s last-write-wins upsert could clobber
newer deliberation the way `-c` could, but without an actor and without a
mistake. Investigated empirically in throwaway `SEEDS_DIR` labs. Split answer:

**The import in isolation is safe.** `export.py:235` compares with a strict
`>`, so a JSONL record that is older *or exactly equal* is skipped and the DB
row survives untouched. v1 records can't clobber at all (create-only,
export.py:116-117). So the literal worry in this seed — "a stale file overwrites
a newer body" — does not happen.

**But `seeds sync` can still destroy newer deliberation silently, and the loss
lands in the export half.** `sync` is import (cli.py:1175) then an
unconditional export (cli.py:1178) that opens the JSONL `"w"` (export.py:100)
and rewrites it wholesale from the DB, never comparing against what was on disk.
Reproduced: machine B appends and pushes; machine A appends later without
pulling; A pulls and a human resolves the conflicted line **in favour of B**; A
runs `seeds sync`; the import correctly skips B's line and the export then
overwrites the file with A's version. B's text is gone from the file and never
reached any database, and the human's explicit merge resolution was reverted
without a word.

**And the timestamp the file claims is never verified.** `export.py:238` passes
`touch=False`, so `db.py:451-452` leaves the JSONL's `updated_at` verbatim; it
is re-exported byte-identical. A one-hour clock skew is enough to invert the
winner. Worse, a *future-dated* record is self-sustaining: after it is imported,
every legitimate local edit sets `updated_at = now_utc()`, which is **earlier**
than the stored future stamp, so the seed's timestamp moves backward and the
poisoned record in git out-ranks every future local edit indefinitely. Confirmed
by repro: a normal `-a` append was destroyed by re-importing the same unchanged
file.

**This sharpens what the seed was really circling.** The concern here was framed
around one flag that needs an actor to mistype it. The import investigation says
the deeper property is the same one in both places: *seeds destroys deliberation
wholesale rather than merging it, and says nothing when it does*. `-c` replaces a
body; LWW replaces a whole row (db.py:454-472). Since `-a` (append) is the normal
editing mode, two machines appending to one seed always lose a side entirely —
there is no path where both survive. The `-c` guard shipped in seeds-884 fixed
the instance; the class is still open.

**The reporting is what makes it invisible**, and that is the cheapest thing to
fix. A discarded record prints `0 created, 0 updated, 1 skipped` — the same line
every unchanged seed produces. A routine sync of this project would say `270
skipped`, so a real loss hides inside a number nobody reads. Distinguishing
"skipped, identical" from "skipped, and the file's content DIFFERS" would surface
both silent paths before the export runs.

Reassuring for now: an audit of all 270 records in `.seeds/seeds.jsonl` found 0
timezone-naive, 0 future-dated, and 0 with `updated_at < created_at`. Nothing is
poisoned today, and `git checkout <old-commit>` + `sync` loses no seeds (it only
leaves a dirty tree carrying later seeds).

Remedy is a design decision, deliberately not taken in the investigation bead.
Options and full evidence are in **seeds-agk** (P1).



---

## Shipped in v0.5.0 (2026-08-11) — and the locked gate did not survive contact

All three beads landed: seeds-884 (`-c` guard), seeds-agk.1 (timestamp validation), seeds-agk.2 (divergence-aware export).

### The `updated_at == created_at` gate was unimplementable as specified

The design above locks on "`updated_at == created_at` means no deliberation has accumulated." That invariant **did not hold**: `Seed` took two separate `now_utc()` readings via `default_factory`, measured ~8 microseconds apart, so **every** freshly created seed already read as edited and `-c` would have refused on all of them.

Making the design work required changing the data model — `Seed.updated_at` now mirrors `created_at` at construction (sentinel + `__post_init__`), plus a `has_been_edited()` predicate. That is a broader change than the bead scoped, and it was necessary for the feature to function at all rather than a nice-to-have.

**Consequence for existing data:** seeds created before that change still carry the microsecond drift, so they read as edited. Measured at the time: **234 of 270 seeds (87%)**. So `--replace` is the ordinary path for anything pre-existing, not the rare emergency the design imagined. Conservative direction, and the refusal message names the escape — but the design's mental model of "`--replace` is for redaction emergencies" is not how it will actually be used for a while.

### What agk.1 and agk.2 shipped

- Import refuses records dated beyond `FUTURE_TIMESTAMP_TOLERANCE` (5 min), killing the self-sustaining poisoning. Timezone-naive stamps are read as UTC instead of raising `TypeError` mid-file.
- `export_to_jsonl` reads the file before overwriting and raises `DivergentExportError`. Guard is default-on **inside** the export so no call site can forget it; `rename-prefix` is the sole sanctioned bypass. Divergence is detected by **content**, never `updated_at`.
- agk.2 closed a hole agk.1 opened: a refused import record never reaches the DB but stays on disk, where the very next export deleted it — quietly undoing the refusal.
- The prefix heuristic ("DB content starts with disk content -> benign append") was validated against 67 commits of real history before being built on: 42 content-changing edits, 41 covered, 1 true divergence.
