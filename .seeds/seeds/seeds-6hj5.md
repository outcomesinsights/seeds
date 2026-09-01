---
id: seeds-6hj5
title: Hallucinated-ID validation can't catch base36 hash refs — shape alone can't distinguish them from prose
status: resolved
type: concern
created_at: 2026-07-27T05:49:19.883990+00:00
updated_at: 2026-08-31T20:02:46.909724+00:00
resolved_at: 2026-08-11T19:45:32.575600+00:00
resolution: "Shipped in v0.5.0 as seeds-90o (bead IDs count as known refs) and seeds-819 (base36 refs validated against a 13-entry bare-suffix prose allowlist). Hash-shaped hallucinations are now caught where they previously passed in silence.\n\nEFFICACY — tweaking needed: MINOR. Planning-miss, and a specific kind worth naming.\n\nThe acceptance criterion asserted 'running the validator over all existing seeds reports zero unknown references.' It reported 2. I predicted the result of a measurement I had not run, which turned a discovery into an apparent failure and created pressure to pad the allowlist until the number matched. The executing agent correctly refused to do that.\n\nWhat a better bead would have said: 'Run the sweep and RECORD what it finds; each hit is either a real hallucination or an allowlist entry.' Never write an acceptance criterion that predicts a measurement's outcome — specify that the measurement happens and gets recorded.\n\nAlso carried: the design itself only emerged after three rounds of Ryan pushing back on an 'it's irreducible' framing that was directionally true but obscured two tractable facts (16 of 24 false positives were just unloaded bead IDs; the remaining 8 were enumerable). The original wrong framing is deliberately preserved above rather than edited out."
tags:
  - ids
  - validation
  - base36
relationships:
  - target_id: seeds-tk5y
    rel_type: relates-to
    created_at: 2026-08-10T17:12:45.160395+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Found while reviewing the seeds-skc fix (2026-07-26). NOT a regression from that work — verified main behaves identically — but the fix makes the gap sharper and more consequential.

## The gap

`_validate_id_refs` (src/seeds/cli.py) exists to catch, in its own words, "the common failure where an agent drafts a body like `see <prefix>-117` with a hallucinated ID." It works for grandfathered sequential IDs and silently does nothing for base36 hash IDs.

Reproduced on a temp database, on BOTH main and the seeds-skc branch:
- creating a seed whose body cites a NONEXISTENT numeric ID -> correctly errors ("seed body references unknown IDs")
- creating a seed whose body cites a NONEXISTENT hash-shaped ID -> silently accepted, seed created

So the guard is dead for exactly the ID scheme that is now standard going forward (see seeds-199).

Live confirmation: the first attempt to create THIS seed was itself rejected — because the illustrative numeric IDs in the draft body tripped the validator, while the illustrative hash-shaped ID in the same body sailed through unchallenged. The asymmetry demonstrated itself.

## Why this is hard, not just unfixed

seeds-skc introduced `_is_id_ref`, which decides whether a matched `<prefix>-<token>` is a real reference by checking membership in a `known_ids` set. That is sound for `rename-prefix`, where you only rewrite IDs you are actually renaming.

It cannot work for validation, and the reason is circular: validation's whole job is to find references that are NOT in the database. Gating on database membership means it can only ever find references that ARE.

The underlying constraint is real and probably irreducible: a hallucinated hash and ordinary prose are **shape-identical**. Base36 is `[0-9a-z]`, which is also just... letters. No regex can separate them. Any validator that flags unknown hash-shaped tokens will false-positive on prose like "seeds" hyphen "related", "seeds" hyphen "only", "seeds" hyphen "first".

## Options worth weighing (none obviously right — that's why this is a seed)

1. **Accept it.** Document that hallucinated-ID validation only covers legacy sequential IDs, and lean on `--allow-unknown-refs` staying rare. Cheapest; leaves the stated purpose of the guard half-met.
2. **Require explicit ref syntax for hash IDs** — e.g. only validate inside `[[...]]` wikilink brackets. Makes refs machine-identifiable by construction. Cost: a convention agents must follow, and bare mentions stay unvalidated.
3. **Length/entropy heuristic.** Hash suffixes live in a 3-8 char window; require at least one digit, or reject dictionary words. Cost: probabilistic, will both miss and false-positive. An all-digit suffix is a valid hash; a 4-letter English word is valid base36.
4. **Validate at a different layer** — a `seeds doctor` check that reports dangling hash-shaped refs as warnings rather than blocking creation. Turns a hard gate into a soft signal, sidestepping the false-positive cost.

Option 2 feels most principled and option 4 most pragmatic; 3 seems like a trap. Not deciding here.

Related: the `--allow-unknown-refs` flag on `seeds create` / `seeds update` exists precisely as the escape hatch for this validator.



---

## Live instance: the seeds<->beads lineage workflow trips this both ways (2026-08-10)

Recording bead lineage inside a seed is *mandated* by the `seeds-to-beads` skill ("cite the originating seed IDs so the executor can recover deliberation context"), and in this repo beads share the `seeds-` prefix with seeds. So every promotion note contains `seeds-`-prefixed IDs that are **beads, not seeds** — and the validator has no way to know that.

Both failure directions were observed in a single session:

- **False positive.** Appending a note citing bead `seeds-230` (all-digit suffix) was REJECTED: "seed body references unknown IDs." It is a perfectly real bead; it is just not a seed. Required `--allow-unknown-refs` to record legitimate, skill-mandated lineage.
- **False negative, same session, same workflow.** An earlier promotion note citing beads `seeds-0y4` and `seeds-80g` (base36 suffixes) sailed through unchallenged — not because those were recognized as beads, but because hash-shaped tokens are invisible to the validator entirely, per this seed.

So the current behavior is the worst of both: it blocks the legitimate case it can see, and waves through the case it cannot. Whichever option this seed eventually takes should account for the fact that `seeds-NNN` in a seed body is *ambiguous by construction* in this repo — it may be a seed OR a bead. Options 2 (explicit `[[wikilink]]` syntax) and 4 (soft `doctor` warning instead of a hard gate) both handle that gracefully; option 1 (accept as-is) leaves `--allow-unknown-refs` as a required step in a documented workflow, which is a smell.



---

## Measured on the real database, and a workable design (2026-08-10)

@aguynamedryan pushed back hard on the framing above — *"Why do we need a regex at all? Just look to see if seeds-whatever is in the seeds ID list, and if not, it's a hallucination"* — then caught the flaw himself mid-sentence: *"Oh, actually, seeds-marketplace would be marked as a hallucination."* Then the decisive question: **do we have a known-good list of those words?**

Nobody had checked. So: scanned all 268 seeds' title/content/resolution with the real `_id_ref_pattern`, collecting every `seeds-*` token that is not a seed ID.

**24 distinct tokens. Classified:**

| what they actually are | count | examples |
|---|---|---|
| real **beads** | 16 | seeds-0y4, seeds-80g, seeds-230, seeds-mlj |
| ordinary **prose** | 8 | seeds-marketplace, seeds-cli, seeds-native, seeds-tool, seeds-generated, seeds-level, seeds-like, seeds-side |
| actual **hallucinations** | **0** | — |

Switching on "not in the seed list -> error" today would produce **24 false alarms and catch nothing.**

### This corrects the framing above

The earlier section claims the problem is irreducible because a hash and a word are shape-identical. That is true but was the wrong emphasis, and it obscured two tractable facts:

1. **16 of 24 are a plain bug, not a paradox.** Beads and seeds share the `seeds-` prefix in this repo, but the validator only loads the *seed* list. Every legitimate bead reference reads as a broken seed reference. Loading bead IDs kills two-thirds of the noise outright.
2. **The remaining 8 are enumerable.** "Cannot distinguish by shape" does not mean "cannot distinguish." You do not need a heuristic when you can just list the exceptions — and the complete list across the project's entire history is eight words. That is a config constant, not a research problem.

Note these are not contrived: `seeds-marketplace` is the actual Claude Code plugin marketplace, and `seeds-cli` is the PyPI name under consideration in seeds-95. Real domain vocabulary, which is why they recur.

### Design (@aguynamedryan's, drawn out over three rounds of pushback)

Check a candidate token against, in order: **seed IDs** -> **bead IDs** -> **a small allowlist of domain terms**. Anything still unmatched is a hallucination — flag it.

The regex stays, but only to extract candidates from free text; it is not doing any judgment. That was a red herring in the earlier framing.

Note this makes validation **stricter** than today, not looser: hash-shaped hallucinations currently pass in silence. Under this design they get caught.

**Maintenance cost:** someone coining a new `seeds-<word>` term in prose must add it to the allowlist. Eight terms across the project's life is roughly one every few months, and the failure mode is a clear error naming exactly what to add — not silent breakage.

This supersedes option 3 (length/entropy heuristic — still a trap) and makes option 1 (accept as-is) unattractive, since `--allow-unknown-refs` would remain a required step in a documented workflow. Options 2 and 4 are still live but no longer necessary to solve the core problem.

Related: seeds-tk5y (the `update -c` footgun, surfaced in the same exchange).



---

## Promoted to beads (2026-08-10)

- **seeds-90o** (P2, bug) — Validator rejects bead references: teach it to load bead IDs alongside seed IDs. The unambiguous half; kills 16 of the 24 measured false positives. Optional-by-design: a project with no beads must be unaffected.
- **seeds-819** (P3, feature) — Enable hallucination checking for base36 IDs via a domain-term allowlist. Seeded with the 8 measured prose terms. **Depends on seeds-90o** (enabling it first would flag all 16 legitimate bead references). Carries the rejection of the length/entropy heuristic.

Both are bead IDs, not seed IDs.

This seed stays open until those land — options 2 (`[[wikilink]]` syntax) and 4 (soft `doctor` warning) remain live but are no longer required to solve the core problem.



---

## Shipped (2026-08-10) — with two documented residuals, not the predicted zero

Both beads landed. `find_id_refs` became `find_id_ref_candidates` (extraction only), and validation now checks seed IDs -> bead IDs -> a 13-entry prose allowlist stored as **bare suffixes**, so any project prefix inherits the vocabulary.

A hallucinated hash ID is now rejected where it was previously accepted in silence — verified before/after against main's code.

### The sweep found 16 unmatched tokens across 270 seeds and 100 beads. Zero were hallucinations.

The 8 measured terms were confirmed; 5 more single-occurrence prose words turned up that the original count missed (`experiment`, `recent`, `specific`, `sweep`, `whatever`), bringing the allowlist to 13.

Three tokens were deliberately **NOT** allowlisted, because they are ID-shaped rather than prose. Allowlisting an ID-shaped token would blind the check to that ID permanently, inverting the point of the list:

| token | where | status |
|---|---|---|
| `seeds-7.1` | seeds-140 content: *"e.g., seeds-1, seeds-7.1"* | **pre-existing** — numeric, so main flags it today too |
| `seeds-k3n` | seeds-199 content: *"a 3-4 char id like \`seeds-k3n\`"* | the ONLY new failure this change introduces |
| `seeds-8su` | seeds-199 **resolution** | field is never validated (create checks title+content; update checks title+content+append) |

So the honest post-change number in validated fields is **2, not 0**. The bead's acceptance criterion predicted zero; that prediction was wrong, and padding the allowlist to force it would have defeated the feature.

### Decision: leave the two prose examples alone

The tempting fix is rewriting those example IDs so they stop matching. Rejected, because the cure is worse:

- Both seeds are long and **resolved**. Surgical mid-body edits are not possible — `-a` only appends, so changing prose requires `-c --replace`, a **full-body replacement** of resolved deliberation, carrying exactly the transcription-loss risk seeds-tk5y exists to prevent.
- The residual only bites if someone **edits those two specific seeds**, and `--allow-unknown-refs` handles it in that moment.
- Trading a guaranteed destructive rewrite of two mature seeds for a hypothetical future papercut is a bad trade.

Recorded here so the next agent to hit it knows it is known and intentional, not an oversight.

### Still open from this seed

Option 2 (`[[wikilink]]` explicit ref syntax) and option 4 (soft `doctor` warning instead of a hard gate) remain live. Neither is needed now, but option 4 would make the residuals above a non-issue — a warning is allowed to be occasionally wrong; a blocker is not. The `resolution` field going unvalidated is also worth a look.
