---
id: seeds-sdhc.3
title: Supersession is marked in place by the agent that learned it, not by a later review pass — and that collapses tend into check --smells
status: captured
type: decision
parent: seeds-sdhc
created_at: 2026-08-31T20:09:38.931133+00:00
updated_at: 2026-09-01T02:33:50.192347+00:00
tags:
  - storage
  - supersede
  - marker
  - tend
  - check
  - format
  - "0.7"
  - 2026-08-31
relationships:
  - target_id: seeds-sdhc.2
    rel_type: relates-to
    created_at: 2026-08-31T20:09:48.139750+00:00
  - target_id: seeds-bp0s
    rel_type: relates-to
    created_at: 2026-08-31T20:09:48.250075+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Settles seeds-sdhc's open items #2 (the supersede marker's concrete form) and #5 (who marks supersession, and when). They are one question in practice: the form follows from who is holding the pen.

## Who: the writing agent, in the same edit — not a later review pass

The agent that just learned an old claim is wrong has the context to say why in one clause. A reviewer three weeks later has to reconstruct it, and will write something vaguer.

**seeds-sdhc is its own proof.** Both of its CORRECTION sections were written inline, by the agent that found the error, at the moment it was found. The practice already exists and works; the format only has to name it.

## What that does to `tend`

`tend` was designed as a review-and-rule pass that would compress at the end. seeds-sdhc already recoiled from that ("tending never destroys"). With marking moved to write time, there is nothing editorial left for `tend` to do — what remains is *noticing* seeds that look like they need attention, which is exactly tier 2 of `seeds check` (seeds-sdhc.2).

**So `tend` collapses into `check --smells` and does not need to be its own verb.** One fewer command, and the surviving one cannot destroy anything by construction.

## The form: a marker in place, never a relocation

Rejected: moving superseded text to a `## Superseded` fold at the bottom. Relocation is a large diff for a semantic no-op, it destroys narrative order, it forces an ordering decision among superseded chunks, and it makes `git log -p` on that region unreadable — the very command the history story depends on.

The marker sits immediately after the heading of the section it retires:

    ## Dolt would give us cell-level merge
    > [!SUPERSEDED] 2026-08-28 — ordinary git line-merge surfaces same-field
    > collisions too, so the 120 MB dependency bought nothing.

    ...original section text, untouched...

- **GitHub alert syntax** renders as a blockquote in every markdown viewer, needs no extension, and greps cleanly (`^> \[!SUPERSEDED\]`).
- **Scope is mechanical:** from the marker to the next heading of the same or higher level. That is the parse rule, and it is the whole parse rule.
- **The reason clause is mandatory** and `check` enforces its presence. A bare marker loses the *why*, and seeds-sdhc is explicit that a conclusion without its reason invites re-litigation — a head saying "Python" invites an agent to propose Go next month.

## Why in-place beats the bottom fold for the naive reader too

The fold's argument was that a grep or a `cat` hits live content first. In practice a grep hit lands *inside* the fold with no indication it is dead. With an in-place marker, the retiring line is a few lines above every hit in the section, so context arrives with the match. The naive reader is better served, not worse.

## Corrections are still the separate case

Unchanged from seeds-sdhc: a fact that turned out false is **replaced in place**, with the prior value in git. Only positions we moved past get marked. Carrying a wrong number forward costs context and risks an agent acting on it; carrying a superseded argument forward is what stops the question being re-litigated.

Relates to seeds-sdhc, seeds-sdhc.2, seeds-bp0s.

RULED (@aguynamedryan, 2026-08-31): tend is dropped outright, not merely collapsed. "tend never really got used." Verified while acting on it — tend was never built at all; it is not a verb, so there is nothing to remove from the code, only from the design. The noticing function stays in check --smells, which is where this seed had already put it.

LIVED TEST, 2026-08-31 — the convention's first real use broke its own rule, and the author was the one who broke it.

Hours after this seed settled the marker grammar, seeds-sdhc.1 acquired a `> [!SUPERSEDED]` block sitting after a PARAGRAPH mid-section, retiring that paragraph while the rest of the section stayed live. The spec (docs/storage-format.md section 6.1) says a marker must be the first non-blank line after the heading it retires and that there is no floating supersession. The strict reader built in bead seeds-4co.2 refused the record — 1 of 314, the only failure in the corpus.

The diagnosis is this seed's OWN distinction, misapplied by me: what was marked was a correction of a false FACT (an earlier draft claimed the conflict file retires seeds-faxd's remediation; that had already been fixed in ccee855). This seed says corrections replace in place and only positions moved past get marked. I reached for the wrong half.

@aguynamedryan ruled 2026-08-31: fix the seed, keep the rule strict. 313 of 314 records already complied, so section-scope is 99.7% compatible with real usage, and a second scope rule would have to be implemented in the reader, the checker and the converter alike. seeds-sdhc.1's block is now an in-place correction with the prior version in git; the corpus has zero floating markers.

What this is evidence FOR: the corrections-replace / reasoning-accumulates line is real but subtle, and it needs to be stated in the agent-facing guidance, not just in the format spec — because the failure mode is not ignorance of the rule, it is misclassifying which side of it you are on.
