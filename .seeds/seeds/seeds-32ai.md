---
id: seeds-32ai
title: Should seed IDs be topic slugs rather than base36 hashes? Seeds outlive beads, so the inherited scheme may be the wrong trade
status: captured
type: idea
created_at: 2026-08-12T13:29:08.424479+00:00
updated_at: 2026-08-31T20:02:46.668263+00:00
tags:
  - ids
  - architecture
  - ai-ux
  - seed-identity
  - beads-inspired
relationships:
  - target_id: seeds-vo56
    rel_type: relates-to
    created_at: 2026-08-12T13:29:18.335195+00:00
  - target_id: seeds-199
    rel_type: relates-to
    created_at: 2026-08-12T13:29:18.446956+00:00
  - target_id: seeds-135
    rel_type: relates-to
    created_at: 2026-08-12T13:29:18.557862+00:00
  - target_id: seeds-sdhc.4
    rel_type: relates-to
    created_at: 2026-08-31T20:09:48.584312+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

@aguynamedryan, 2026-08-12 (thinking aloud, explicitly undecided):

> "An alternative might be for the seed ID itself to go from being a hash to being a dashed phrase or sentence that contains kind of the overall topic of the seed... the lodestone for seeds is beads and beads has done a base 36 hash for its IDs all the time. I don't know if that's to save on tokens or what. beads does seem to have a notion that a bead is not ephemeral, but like serves a purpose and then goes away... Whereas seeds are a little bit more long-lasting, so there might be some benefit to changing the way the ID works around. I'm going to just sit and think about this, but I'm still not sure. And I don't know whether or not having a title as id would be helpful enough."

Follows directly from seeds-vo56 (agents cite bare IDs; @aguynamedryan cannot follow). A self-describing ID would dissolve that at the source rather than relying on agent behaviour.

## Correcting one premise: base36 was never about tokens

seeds-199 records the actual reason, and it is neither tokens nor lifespan: **multi-host collision.** The old next_id() scanned local state and returned max(seq)+1, so one git-backed repo worked from two machines minted the same number independently, surfacing only when the JSONL merged. Hash IDs need no shared counter, so that class of collision disappears. Generation is SHA-256 over content + nanosecond timestamp + nonce, with a DB check and nonce-bump retry.

A slug derived from a title does NOT reintroduce the counter problem — there is nothing to coordinate — so this is not a re-litigation of seeds-199 on its own terms.

## The genuinely new axis: seeds-199 optimised for TYPEABILITY, not MEANING

seeds-135 originally chose sequential IDs *for readability* — "seed 12" over an opaque hex hash — so legibility was already first-class in seeds' ID design. seeds-199 then claimed to preserve it: "This keeps the readability that motivated seeds-135 (a 3-4 char id is as typeable as seeds-42)."

But a 3-char hash is only as **typeable**. It is exactly as **meaningless**. The readability goal was silently narrowed from "I can tell what this is" to "I can type it without errors," and nobody noticed. seeds-vo56 is the bill for that narrowing.

So this proposal targets an axis the decision record never weighed.

## Steelman of the lifecycle intuition

@aguynamedryan's guess about *why* beads hashes was wrong, but the instinct may hold on other grounds: **amortisation**. A bead is created, worked, closed, eventually compacted (bd compact exists for exactly that) — read a handful of times over days. A seed is read and re-read for months; this database spans 2026-02 to now and February seeds are still being cited today. The per-read cost of an opaque ID is paid far more often for a seed, even though the one-time minting concern is identical.

That is a real argument for seeds and beads diverging here — and it is not the argument he made, so worth separating.

## Strongest objection: seeds evolve, identifiers must not

A slug fixes the topic at creation. Seeds routinely outgrow their opening framing — three cases from one session:

- **seeds-tk5y** was captured as "update -c silently replaces content," a small CLI footgun. It became the umbrella for the whole sync data-loss investigation. A slug naming the -c flag would now actively mislead about a seed that is mostly about sync.
- **seeds-gf69** opened as "should we ship a flake?" and resolved as "yes, including the home-manager half the consulted specialist advised against."
- **seeds-6hj5** opened arguing the problem was irreducible and closed with a working design drawn out over three rounds of pushback.

Rename the slug to track the drift and every existing reference breaks — including **cross-database** ones, since beads cite seeds as Source: provenance (seeds-171 flagged that hazard; seeds-199 rejected a full renumber partly for it). A bead this month (seeds-90o) already dealt with beads and seeds sharing a prefix; ID churn makes that worse.

An identifier that must never change and a description that must stay current are **different jobs**. Fuse them and one is always wrong.

## New objection, surfaced while writing this seed

Creating this very seed was REJECTED by the hallucinated-ID validator, because the prose quotes two illustrative ID formats that are not real seeds. That is the seeds-6hj5 problem in miniature — and it argues against slugs specifically.

A hash like seeds-d773 essentially never occurs by accident in English. A slug like `seeds-compact-json-output` is *made of words*, so ID-shaped tokens would start appearing in prose constantly — every discussion of a topic would look like a reference to it. Slug IDs would make the prose-versus-reference ambiguity substantially worse, and that check exists precisely because that ambiguity already costs us. Note the escape hatch was needed here on a seed *about* IDs; slugs would make that routine rather than exceptional.

## The middle path this suggests

Keep an opaque stable identity, pair it with a mutable human label, and make the *rendered reference* carry both. Precedents: git (short SHA + subject), Rails migrations (timestamp for identity, slug for humans), Wikipedia (slug URLs with redirects preserving the old ones).

**seeds already has both halves.** Stable identity is the hash; the mutable label is `title`, which seeds-vo56 measured at a median 74 characters and found a good gloss on 268 of 270 seeds. What is missing is not a field — it is that the canonical *reference form* is the bare ID rather than id-plus-title.

That reframes the question from "change the ID" to "change what an ID reference renders as," which costs no migration and breaks no provenance.

## Open

@aguynamedryan is sitting with this; nothing decided. The live question: is rendering the gloss everywhere sufficient — in which case this collapses into seeds-vo56 and no ID change is needed — or does only a self-describing identifier survive agent inattention, in which case the drift, cross-reference, and prose-ambiguity costs all have to be paid and priced.

Related: seeds-vo56 (the symptom), seeds-199 (base36 decision), seeds-135 (original readability motivation), seeds-140 (prefix configurability + rename machinery), seeds-171 (cross-database provenance), seeds-6hj5 (prose-versus-reference ambiguity).
