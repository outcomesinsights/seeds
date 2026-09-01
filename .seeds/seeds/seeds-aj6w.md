---
id: seeds-aj6w
title: "Add --add-tag / --remove-tag: wholesale --tags forces agents into lossy read-modify-write"
status: resolved
type: idea
created_at: 2026-08-10T17:27:28.209866+00:00
updated_at: 2026-08-31T20:02:47.769900+00:00
resolved_at: 2026-08-11T19:46:05.976396+00:00
resolution: "Shipped in v0.5.0 as seeds-3ps: --add-tag / --remove-tag on seeds update, repeatable, silent no-op on an absent tag, authored order preserved, wholesale --tags untouched.\n\nEFFICACY — tweaking needed: NONE. Shipped as specified, plus two calls that improved on it (rejecting the same tag passed both ways; skipping the DB write on a no-op so a typo cannot arm the -c guard from seeds-tk5y — a cross-seed interaction neither seed predicted).\n\nThe lesson here is not about the bead, which was fine. It is about how the seed nearly did not get written.\n\nI had assessed this as marginal ergonomics: retyping four tags is not a hardship. Ryan's reframe — 'Remember, I don't actually ever use the CLI for seeds. It's all completely run by you' — inverted it. A human retyping their own tags notices one went missing. An agent reproducing a list from a seeds show it read two steps earlier does not, and nothing validates the write. Same silent-loss shape as the -c footgun, which is what made it worth doing.\n\nCarry forward: before pricing an ergonomics change, establish WHO actually runs the command. 'Mildly annoying for a human' and 'silently lossy for an agent' are the same feature request with opposite priorities. Measuring the real workflow (next-post live on 11 seeds, 70 other tags to retype, tags like meets-me-where-i-am) is what turned the reframe into evidence.\n\nStill unproven: the next-post flag has not actually been cleared yet, so the ergonomic win is available but untested in practice."
tags:
  - cli
  - tags
  - agent-ux
  - correctness
  - data-loss
converted_at: 2026-09-01T05:20:22.746832+00:00
---

`seeds update --tags` replaces the entire tag set (`seed.tags = [...]`, cli.py:830). There are no additive operations — verified, zero matches for `add_tag`/`remove_tag` in src/. So changing one tag requires reading all of them and retyping the rest.

Surfaced 2026-08-10 while deciding whether `--tags` needed the same guard as `--content` (seeds-tk5y). It does not — tags are working state, replacement is their normal verb. But the discussion exposed this instead.

## The reframe that makes this a correctness issue, not ergonomics

@aguynamedryan: *"Remember, I don't actually ever use the CLI for seeds. It's all completely run by you."*

That inverts the analysis. A human retyping their own tags would notice one went missing. An **agent** reproducing a list from a `seeds show` it read two steps earlier will not — and neither will anyone else, because nothing validates that the other tags survived. It is the same silent-loss shape as the `-c` footgun, and the same reason it is worth fixing: the failure produces no signal.

## Measured cost of one real, pending workflow

The `next-post` flag is live on **11 seeds** today (queued blog posts). Clearing it after publication currently requires, per seed: one `seeds show` to read current tags, then `--tags` with everything else retyped.

**11 reads, 11 writes, 70 other tags retyped**, each a silent-loss opportunity.

The tags being retyped are long and idiosyncratic — `meets-me-where-i-am`, `deliberation-is-the-artifact`, `destination-vs-journey`, `available-not-lived`, `code-as-specification`. seeds-196 carries 10 tags; removing one means correctly reproducing nine of those.

This is not hypothetical: those 11 seeds are queued, and the flag will be cleared.

## Why flag-style tags are the recurring case

Tags in this database split into two kinds, and only one churns:

- **Topical** (`workflow` 37x, `architecture` 34x, `ai-ux` 28x) — set at creation, never touched. Wholesale `--tags` is correct for these.
- **Transient markers** (`next-post` 11x, date tags like `2026-06-23` 9x) — added to a batch, then cleared once handled. These are the flag/unflag cycle, and they are the entire reason additive operations are needed.

74% of seeds (200/269) carry tags, across 317 distinct tags, so seeds are richly tagged and the retyping burden is not a corner case.

## Proposal

Add `--add-tag` and `--remove-tag` (each repeatable) alongside the existing wholesale `--tags`. Keep `--tags` — it is the right verb at creation and for a deliberate full reset.

Secondary benefit, related to seeds-d773: read-modify-write costs an extra read per seed to change a few bytes. `--remove-tag next-post` costs none.

## Open

- Should `--remove-tag` on a tag the seed does not carry be a silent no-op, or an error? Silent is friendlier for batch operations ("clear this flag everywhere"); an error catches typos like `--remove-tag next-posts`. Leaning silent no-op with the removal count reported, so a typo shows up as "0 removed."
- Is a batch form worth it (`seeds update --remove-tag next-post --all-tagged next-post`), or is looping over IDs fine? Looping is fine at 11 seeds; revisit if flags routinely span dozens.



---

## Open questions resolved (2026-08-10)

@aguynamedryan: *"I agree that remove tag should be a silent no op. I say looping is fine for now."*

- **`--remove-tag` on a tag the seed does not carry: silent no-op**, reporting the removal count. A typo like `--remove-tag next-posts` surfaces as "0 removed" rather than erroring mid-batch or vanishing without trace.
- **No batch form.** Looping over IDs is fine at the current scale (11 seeds carrying `next-post`). Revisit only if flags routinely span dozens.



---

## Promoted to beads (2026-08-10)

- **seeds-3ps** (P2, feature) — Add `--add-tag` / `--remove-tag` to `seeds update`. Bead ID, not a seed ID. Carries both of @aguynamedryan's rulings (silent no-op on absent, no batch form) plus the locked decision to keep wholesale `--tags` and add no guard to tag operations.



---

## Shipped in v0.5.0 (2026-08-11)

seeds-3ps landed as specified: `--add-tag` / `--remove-tag`, both repeatable, silent no-op on an absent tag reporting the count, authored order preserved, wholesale `--tags` untouched, no guard on tag operations.

Two calls made beyond the spec, both improvements on it:

1. **Passing the same tag to both `--add-tag` and `--remove-tag` is rejected**, naming the tag, rather than resolved by an invented precedence rule. Consistent with rejecting `--tags` + additive flags, and for the same reason: a silent surprising outcome is exactly the failure this seed exists to eliminate.
2. **A no-op tag request skips the database write entirely.** This matters because of a cross-seed interaction nobody anticipated: without it, a typo'd `--remove-tag` would bump `updated_at`, which silently arms the `-c` guard from seeds-tk5y on a seed nobody actually edited. Neither seed predicted that interaction.

The `next-post` flag that motivated the measurement is still on 11 seeds — the workflow this unblocks has not been run yet, so the ergonomic win is available but unproven in practice.
