---
id: seeds-lcfa
title: Would switching to Dolt let the seeds DB live in the git repo the way beads does?
status: captured
type: question
created_at: 2026-08-26T03:35:01.124113+00:00
updated_at: 2026-08-31T20:02:49.076835+00:00
tags:
  - architecture
  - storage
  - dolt
  - beads-inspired
  - sync
  - merge
  - 2026-08-25
relationships:
  - target_id: seeds-42
    rel_type: relates-to
    created_at: 2026-08-26T03:35:17.931292+00:00
  - target_id: seeds-44ht
    rel_type: questioned-by
    created_at: 2026-08-26T03:35:18.045001+00:00
  - target_id: seeds-rlc2
    rel_type: relates-to
    created_at: 2026-08-26T03:52:29.225511+00:00
  - target_id: seeds-fkb8
    rel_type: relates-to
    created_at: 2026-08-28T16:32:59.990049+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Open question: should seeds swap SQLite for Dolt as its storage engine, so the database itself is git-embedded the way beads' is?

Worth checking the premise first — beads does NOT git-track its Dolt data. Verified in this repo (2026-08-25): `git ls-files .beads` lists only `issues.jsonl`, `metadata.json`, `config.yaml`, `export-state.json`, and the hooks; `.beads/embeddeddolt/` and `.beads/dolt/` are gitignored local state. Beads syncs through the git-tracked JSONL export, with no Dolt remote. That is architecturally the SAME thing seeds already does with `.seeds/seeds.db` (ignored) plus `.seeds/seeds.jsonl` (tracked).

So "embed the DB in the repo like beads" is not actually the delta. If Dolt is worth adopting, the reasons have to be the things Dolt gives that SQLite does not:
- Real data-level merge instead of JSONL line-merge — matters if seeds get edited concurrently on multiple hosts/worktrees and the JSONL conflicts get ugly.
- Cell-level history and time travel over the seed graph — arguably interesting for a tool whose whole thesis is capturing a deliberation's evolution. That is the argument most native to what seeds is for, and it is about provenance, not portability.
- Branch-per-exploration semantics for the seed DB itself.

Costs to weigh:
- Beads is Go and can link Dolt in-process. seeds is Python — there is no in-process embedded Dolt for it, so this means shipping/managing a dolt binary or a sql-server process. Note that beads RETIRED shared server mode in favour of embedded; seeds would be adopting the mode beads abandoned.
- Loses the "it's just a SQLite file plus a JSONL" simplicity, which is currently a real virtue for a small CLI.
- The JSONL export would probably still exist for human/agent readability and cross-tool consumption, so this adds a layer rather than replacing one.

Framing question to settle before any of the above: what problem are we actually feeling? If it is "my seeds.jsonl conflicts when I work on two machines," Dolt is one answer but so is a smarter merge driver or per-seed files. If it is "I want to see how a seed's thinking changed over time," that is a provenance feature that could be built on SQLite without a new engine.

Related: seeds-42 (deferred — would a graph DB beat SQLite if relationships become central?) is the same class of storage-engine question, and any answer here should probably answer that one too. Also touches seeds-10 (JSONL export format) and seeds-155 (a `seeds import` command).


--- WHERE THIS LANDED (2026-08-25, after the full deliberation) ---

The question was asked as "should we adopt Dolt," and the honest answer that came out of six children of investigation is: the premise was wrong in a useful way, and the real answer is smaller and cheaper than Dolt.

WHAT THE PREMISE TURNED OUT TO BE. Not "embed the DB in git" — seeds already has that. The felt pain (@aguynamedryan, this session) is cross-host sync: "hooks dump the DB to JSONL, and then someone has to REMEMBER to pull the JSONL back into the local DB, and it feels rickety." That decomposes into two independent problems (seeds-lcfa.1): nothing is wired to run the import, and the import that does exist is whole-record last-write-wins that silently drops the losing edit.

WHAT DOLT WOULD ACTUALLY COST (seeds-lcfa.3, all measured on titan): a 120 MB binary, no maintained embedded Python path (doltpy deprecated, doltcli unmaintained since 2023), so either ~90 ms per shelled-out query — as much as an entire seeds command costs today — or the sql-server mode beads tried and RETIRED. Plus a 571-test suite that runs in 16.1 s today and would degrade to minutes inside the pre-commit and pre-push gates.

WHAT A GO REWRITE WOULD AND WOULD NOT FIX (seeds-lcfa.5): it fixes the process model completely, and it does not make the size go away — it internalizes it. The real bd binary is 137 MB with 16,695 dolthub/dolt symbol references. You trade "install a 120 MB binary" for "our tool IS a 137 MB binary."

WHAT DOLT WOULD NOT FIX AT ALL (seeds-lcfa.2): worktrees. That is path resolution, already decided in seeds-191, and it should proceed independently of everything here.

THE ANSWER THAT EMERGED (seeds-lcfa.4 option C, prototyped in seeds-lcfa.6): store each seed as its own file and let GIT be the merge engine. Different seeds never collide; different fields of one seed are different lines and merge cleanly; a real same-field collision becomes an ordinary git conflict in readable text that a human or agent resolves — which is the behaviour we want and precisely what CRDTs refuse to give. It delivers the history win for free (`git log -p` on one seed IS its field-level evolution, which is the most on-thesis capability Dolt was offering) and it makes the "which side is the source of truth, did I remember to import" problem structurally impossible rather than patched with hooks. Measured cost: 2.3x disk from block granularity, and full-text search is the one genuine casualty.

TENTATIVE DISPOSITION: Dolt is not the answer for seeds; the engine was never the problem. This seed should probably resolve as "no" once the per-seed-files path is decided on its own merits — but it should NOT resolve until then, because the Dolt-shaped wins (cell-level conflict reporting, SQL-queryable history) are the bar the replacement has to clear.


--- PREMISE CORRECTION (2026-08-26) ---

The opening premise above - "beads syncs through the git-tracked JSONL export,
with no Dolt remote" - was verified against THIS repo's .beads/ and remains true
here: seeds' own beads is single-host, with no sync.remote and no refs/dolt/*.
As a statement about beads-the-tool it is now false. home-manager moved its
beads to a git-backed Dolt remote at refs/dolt/data on 2026-08-26.

This does NOT move where the deliberation landed, and the reason is the
interesting part: beads' move was forced by a two-day silent divergence in which
three hosts ran disjoint databases and each commit deleted the others' work -
with Dolt's cell-level merge present and working throughout. The engine was
never what was broken; the wiring was. The full correction is in seeds-lcfa.3.


CORRECTION TO THE CORRECTION (2026-08-26, same day): the paragraph above says
Dolt's cell merge was "present and working throughout" the home-manager
divergence. @aguynamedryan's read is that the churn was misconfiguration between the three
hosts, and he is right - the merge was never REACHED, because the databases
never met. So that incident is much weaker evidence about Dolt-for-seeds than
this seed implied; the ledger's conclusion rests on the measured costs in
seeds-lcfa.3, not on it. Full recalibration there.
