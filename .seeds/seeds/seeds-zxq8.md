---
id: seeds-zxq8
title: The supersede rule is stated, but the CLI has no light route for an in-place fact correction, and the skills still say to append corrections
status: captured
type: question
created_at: 2026-09-30T19:26:06.654470+00:00
updated_at: 2026-09-30T19:56:07.116536+00:00
---

**The question:** The supersede discipline is now stated in `seeds prime` and `update --help` (bead seeds-2ya, 2026-09-30): a FALSE fact is replaced in place; a position that was MOVED PAST is kept and marked `> [!SUPERSEDED] YYYY-MM-DD — <reason>`. But the CLI and the shipped skills don't make the first half practical, and the skills steer agents away from the second.

**Found while implementing seeds-2ya (the implementing agent's related-defects), and verified 2026-09-30:**

1. **No sanctioned route for an in-place fact correction.** `seeds update --content/--content-file/-` is refused on any non-empty body (seeds-atw). The only way through is `--content-file F --replace`, which means rewriting the WHOLE body into a file to fix one fact. `update --help` frames `--replace` as "discard it deliberately", the same wording used for throwing a deliberation away, not for correcting it. So an agent that follows prime's rule has two options: a heavy full-body replace whose help text calls it discarding, or a direct file edit, which prime discourages elsewhere.
2. **The skills still say "append the correction".** winnow ("Contradiction upheld": "Append the correction to the superseded seed with `seeds update <id> --append`") and resolve-seeds-from-beads (reconciliation: "append them to the relevant seed"). Appending leaves the overtaken text in place, UNMARKED. A contradiction that is upheld is usually a position moved past, which should get a marker. seeds-2ya added a one-line pointer to both skills and left the append instruction unchanged.

**Open:**

- Should seeds have an in-place edit verb, for example `seeds update <id> --edit OLD NEW` or a `seeds correct`, that changes one span and bumps updated_at? Or should `--content-file F --replace` be documented as the sanctioned correction route, with the help text reworded so it isn't only "discard"?
- Should `seeds supersede <id> --heading H --reason R` insert the marker, so agents don't hand-write the grammar?
- Should winnow and resolve-seeds-from-beads mark upheld contradictions as superseded instead of appending, or append AND mark?
- Related: seeds-sdhc.3 (the discipline, now resolved as shipped) and the unsuperseded-long-body smell, which grows each time a correction is appended without a marker.

## Evidence gathered 2026-09-30, before the ruling

Across the ~2,000 seeds in all non-archived stores, `> [!SUPERSEDED]` appears in 2 seeds, both in the seeds repo. Appended CORRECTION / UPDATE / RULED paragraphs appear in about 290 seeds (code_set_catalog 93, code_collector 48, seeds 33, icd10cm 30, home-manager 29, ...). Agents and skills append; they do not mark. The unsuperseded-long-body smell fires 44 times in code_set_catalog and 11 in seeds. seeds-atw's discard guard (every non-empty body, 2026-09-30) made in-place fact correction HARDER: one fact now needs a whole-body rewrite plus --replace.

## RULED (Ryan, 2026-09-30): option C, a hybrid

- **A fact that turned out FALSE is corrected in place**, with a new narrow tool: `seeds update <id> --edit OLD NEW` replaces one exact, unique span, refuses if OLD is missing or appears more than once, and bumps updated_at. It is an edit, not a discard, so it needs no --replace. This is the one case where a stale sentence does real harm: a reader who stops early acts on the wrong fact.
- **A position that was MOVED PAST is recorded by appending a labelled, dated note** (RULED / UPDATE / CORRECTION YYYY-MM-DD: ...). That is what ~290 seeds already do. The `> [!SUPERSEDED]` marker becomes optional: still valid grammar, still parsed, no longer required.
- Rejected: A (full tooling for both halves: `--edit` plus a `seeds supersede` marker command), because the marker half has been used twice in the fleet's history. Rejected: B (append-only), because it leaves a false fact above its correction.

## Consequence to carry into the beads

The unsuperseded-long-body smell exists to ask for markers on long, much-edited bodies. Under C a long body with appended notes and no marker is the norm, so the smell as written nags against the rule. Retire it or retune it (for example, to flag a body with neither a marker nor any dated note). This follows from C, but it is a judgement, so the implementing bead should record its pick.
