---
id: seeds-ikkx
title: Where the gate's confirm escape lives, and whether updated_at should count as a mass rewrite
status: captured
type: question
created_at: 2026-10-27T20:46:27.929996+00:00
updated_at: 2026-10-27T20:46:27.929996+00:00
---

The fix for bead seeds-uk5p is not ruled. That bead reports that SEEDS_GATE_CONFIRM=1 does not pass `seeds check --against-git`, and gator's standard pre-commit recipe runs exactly that command. Reported by the roobetl session on 2026-10-27.

## Question 1: where should the escape live?

- (a) gator's recipe changes to `seeds check --gate`. This is the one-line recipe that `seeds check --help` documents. `--gate` also passes silently where there is no store, so gator's `[ -d .seeds ]` guard becomes redundant. Cost: a change to gator's standard, which reaches every adopted repo.
- (b) seeds honours SEEDS_GATE_CONFIRM in plain `--against-git` too. Every existing wiring works with no change in gator. Cost: `--against-git` is also a read-only diagnostic, and an environment variable would change its exit code.
- (c) Both.

Agent lean: (a). `--gate` is the documented commit-path command, and it already holds the escape. In either case, the help text must stop saying that the escape works "however the gate is wired".

## Question 2: should updated_at count toward mass-field-rewrite?

Every edit through seeds bumps updated_at. So in a small store, ordinary work trips the rule: 10 of 40 seeds edited is 25%, over the 20% / 10-seed threshold. The rule exists for seeds-wurl, where a sweep replaced 83 of 306 titles. A changed updated_at alone shows that seeds edited the file, which is the expected path. A body change without an updated_at change is already its own finding.

Options: drop updated_at from the compared fields; keep it but count only seeds where a content field also changed; or keep it as is and rely on the escape. Not ruled.
