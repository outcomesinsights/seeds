---
id: seeds-lcfa.3
title: "Dolt ledger: measured gains and costs for seeds specifically (titan, 2026-08-25)"
status: captured
type: exploration
parent: seeds-lcfa
created_at: 2026-08-26T03:45:30.621668+00:00
updated_at: 2026-08-31T20:02:49.337021+00:00
tags:
  - architecture
  - storage
  - dolt
  - tradeoffs
  - measured
  - distribution
  - testing
  - 2026-08-25
relationships:
  - target_id: seeds-sdhc
    rel_type: relates-to
    created_at: 2026-08-28T17:36:41.421897+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

The gains-vs-costs ledger for adopting Dolt, with the numbers measured on titan on 2026-08-25 rather than recalled. dolt 1.82.4 is installed here; upstream is 2.3.1.

WHAT DOLT WOULD GIVE

1. Conflict-correct merge. This is the one that answers the actual pain in seeds-lcfa.1. Dolt merges per CELL and surfaces genuine collisions in `dolt_conflicts_<table>`. Seeds today does whole-record last-write-wins on `updated_at` and silently discards the loser. Dolt turns a silent data-loss path into a reported conflict. Nothing else on this list is load-bearing.

2. Real history over the seed graph. `AS OF`, `dolt_log`, `dolt_diff_seeds` — field-level evolution of a seed, queryable in SQL. Today the DB keeps a single `updated_at` and NO history whatsoever; the only record of how a seed's thinking changed is git's line-diff of a JSONL blob. For a tool whose entire thesis is capturing how thinking evolved, that gap is embarrassing, and this is the most on-thesis thing Dolt offers.

3. Branches over the data. Branch-per-exploration, or branch-per-worktree. Note seeds-lcfa.2: the worktree version reopens a decision seeds-191 already settled the other way.

4. Optional: `dolt push/pull` to a remote could replace the JSONL round-trip outright. Worth flagging that beads does NOT do this — it syncs via git-tracked JSONL and keeps Dolt purely local — so the precedent from the tool we would be copying is against it.

WHAT DOLT WOULD INTRODUCE

1. A 120 MB Go binary, in a pip-installable public CLI. Measured: `/usr/local/bin/dolt` is 120 MB. seeds is on GitHub as outcomesinsights/seeds, MIT, Beta, `requires-python >=3.10`, and its runtime dependencies are exactly `click` and `flask` — both pure Python. `uv tool install seeds` currently yields a working tool with nothing outside the wheel. After Dolt, every user and every contributor needs a 120 MB non-Python binary on PATH. That is the single biggest cost and it is a distribution cost, not a code cost.

2. No in-process option from Python. Beads links Dolt in-process because beads is Go; there is no maintained Python binding that does the same. That leaves two paths and both are bad:
   - Shell out per query. Measured: `dolt sql -q` costs ~90 ms per invocation, essentially all process startup. For comparison, seeds' ENTIRE current command latency is 158 ms for `seeds list` and 113 ms for `seeds show` (which includes ~90 ms of Python interpreter startup). One shelled-out query costs about as much as a whole command does today; any command issuing several would visibly regress.
   - Run `dolt sql-server` and talk MySQL wire protocol. That is a background process lifecycle, a port, a lock, and a new driver dependency — and it is precisely the shared-server mode beads TRIED AND RETIRED in favour of embedded. Seeds would be adopting the mode its own model abandoned, without the escape hatch that made abandoning it possible.

3. The test suite. Measured: 571 tests, 16.1 s, using ephemeral SQLite files. `dolt init` alone is 84 ms; add per-test server startup or ~90 ms per query and the suite goes from seconds to minutes. This is not academic — pytest runs in pre-commit on EVERY commit, and pre-push runs the full suite across four Python versions. A slow suite here degrades the gate that keeps billed CI green.

4. Nix and CI packaging. The repo has a flake.nix and `nix flake check --all-systems` runs in both CI and the pre-push gate. A 120 MB non-Python runtime dependency has to be threaded through the derivation and the CI image.

5. Debuggability regression. `seeds.db` can be opened with any sqlite3 and `seeds.jsonl` with any text tool. Dolt's store is a chunk store — inspectable only through dolt itself.

6. Version skew becomes a maintenance surface. This host is pinned three minor versions behind upstream (1.82.4 vs 2.3.1). Storage-format compatibility across hosts running different dolt versions is a new class of problem that a single-file SQLite DB does not have.

7. Storage growth, minor: beads' `.beads/embeddeddolt/` is 12 MB against a 244 KB `issues.jsonl` — roughly 50x. Gitignored either way, so this is disk noise, not a real objection.

8. The JSONL does not go away. It is what agents and humans read, what the divergence guard checks against, and what git actually merges. Dolt ADDS an engine; it does not remove a layer — unless we go all the way to a Dolt remote, which means standing up hosted infrastructure and holding a second source of truth alongside git.

WHAT IS *NOT* A REAL COST, so it should not be argued either way: the SQL port. Measured surface is small — 4 tables (seeds, relationships, config, plus their re-declarations), 9 sqlite3 call sites, and about 15 SQLite-specific constructs (6 `INSERT OR IGNORE`, 4 `PRAGMA`, 2 `AUTOINCREMENT`, 1 `INSERT OR REPLACE`, 1 `strftime`). Porting that to MySQL dialect is an afternoon. The dependency and process-model costs are the whole argument; the code change is noise.

THE CHEAPER ALTERNATIVE THAT SHOULD BE PRICED FIRST
Every gain above except cell-level merge is reachable without leaving SQLite:
- Auto-import on merge/checkout via git hooks — kills the "remember to" ricketiness (seeds-lcfa.1 problem 1). Costs nothing.
- Replace silent whole-record LWW with per-field timestamps or an explicit conflict flag — captures the CORRECTNESS core of the merge argument without the engine. Two hosts editing different fields merge cleanly; a real collision gets reported instead of vanishing.
- An append-only revision log table in SQLite — delivers gain 2 (a seed's evolution over time), which is the most on-thesis win, in pure Python.
If those three land and the pain is gone, Dolt was never the answer. If they land and same-seed collisions are still routinely lossy, that is the evidence that justifies the 120 MB.


--- PREMISE CORRECTION (2026-08-26): gain 4 above was falsified within a day ---

Gain 4 said a Dolt remote "could replace the JSONL round-trip outright" and then
flagged the precedent as against it: "beads does NOT do this - it syncs via
git-tracked JSONL and keeps Dolt purely local." That parenthetical is now wrong.

WHAT WAS ACTUALLY TRUE, precisely. The 2026-08-25 observation was made against
THIS repo's .beads/, and it still holds here: seeds' own beads is single-host,
.beads/config.yaml carries no sync.remote, `git for-each-ref refs/dolt/*` is
empty, and the JSONL round-trip really is the sync channel. What was wrong was
the GENERALISATION to beads-the-tool. beads supports a git-backed Dolt remote at
the non-branch ref refs/dolt/data, and home-manager adopted it on 2026-08-26
(commit 9c58541). beads' own `bd config --help` now says of the JSONL export:
"It is not cross-machine sync; use bd dolt push/pull with a Dolt remote."

WHAT THE NEW PRECEDENT ACTUALLY SAYS - and it is worse for Dolt, not better.
home-manager did not move to the Dolt remote because the JSONL was inelegant. It
moved after a two-day silent data-loss incident:
- From 2026-08-24 to 2026-08-26, sync.remote was present in .beads/config.yaml.
- That single line makes beads' post-merge hook SKIP the JSONL import
  ("post-merge: skipping JSONL import because sync.remote is configured").
- Nothing was wired to run `bd dolt push` / `bd dolt pull` in its place.
- So boost, molt and titan ran three disjoint databases, and each commit's JSONL
  export deleted the other hosts' work. Bead counts ping-ponged 46/47 <-> 81
  across roughly 20 commits before anyone noticed.
- Recovery was a hand-reconciled 102-bead union (commit 91631e1) plus a 146-line
  procedure doc, because a wedged embedded-Dolt database closes every `bd` route
  out and has to be opened with the standalone dolt CLI.
- Aggravating factor: bd REWRITES sync.remote itself to match
  `git remote get-url origin` and commits the change, so hosts whose origin URLs
  differed (molt ssh vs boost/titan https) flip-flopped the line between them.

THE LESSON THAT TRANSFERS TO SEEDS. Dolt's cell-level merge - the one gain in
this ledger that was called load-bearing - was present and working for the whole
incident and it prevented NOTHING, because the failure was in the wiring around
the engine, not in the engine. What fixed home-manager was not Dolt. It was that
something finally RUNS on both sides of the git operation: `just pull` ->
`bd dolt pull`, pre-push gate -> `bd dolt push`, with the push side a HARD FAIL
so a host that cannot publish its beads cannot publish its commits either. The
pull side is deliberately non-fatal so a wedged DB cannot block a config switch.

Seeds can have that same property today, on SQLite, for free: it is precisely
seeds-lcfa.1.1, still captured and unbuilt. So the correction STRENGTHENS this
ledger's closing paragraph rather than undermining it. "Price the cheaper
alternative first" now has a measured example behind it of the expensive
alternative failing at the same task, for reasons the expense did not address.

ONE COST THAT DID NOT MATERIALISE, recorded so it is not re-litigated: a beads
release note gates v1.0.5 as containing a migration (0043) that "can silently
and unrecoverably break multi-machine bd dolt sync after both clones upgrade"
(issue #4259). Checked 2026-08-26: the installed bd is 1.1.2, past that release,
and home-manager's sync was rebuilt after it. So this is history, not a live
risk - but it is a fair data point on how young the Dolt-remote path is.


--- RYAN'S READ ON THE INCIDENT (2026-08-26), and a recalibration it forces ---

@aguynamedryan, on the home-manager churn recorded in the section above: "the churn in
home-manager was misconfiguration between the three hosts as far as I know."
Recorded with his hedge intact. It is the right correction, and the section
above leaned harder on that incident than the facts support.

WHAT WAS ACTUALLY MISCONFIGURED, so this is checkable rather than a vibe:
1. sync.remote was present in .beads/config.yaml from 2026-08-24, which switches
   beads' post-merge hook OFF the JSONL import - and nothing was wired to run
   `bd dolt push` / `bd dolt pull` in its place. Half a migration: the old path
   disabled, the new path never connected.
2. The three hosts disagreed with each other. molt's `git remote get-url origin`
   was ssh while boost's and titan's were https, and bd REWRITES sync.remote to
   match origin and commits the change - so the line flip-flopped host to host.
Neither of those is Dolt malfunctioning. Both are setup that was incompletely
applied on each host and inconsistent between them.

WHAT IS NO LONGER FAIR TO SAY, and it was the load-bearing sentence of the
previous section: that Dolt's cell-level merge "was present and working the
whole time and prevented NOTHING." It prevented nothing because it was never
REACHED. The three databases never met, so there was never a merge to perform.
That is a fact about plumbing, not a demerit against the merge engine, and
citing it as evidence against Dolt was wrong.

THE RECALIBRATION. The previous section claimed the incident "STRENGTHENS this
ledger's closing paragraph." Overstated - withdraw that. An inconsistently
configured three-host rollout says very little about whether Dolt is the right
STORE for seeds. The ledger's conclusion still stands, but it stands on the
measured costs in this seed (120 MB, no maintained Python path, ~90 ms/query,
the test suite) - not on this incident.

WHAT STILL TRANSFERS, at its real and much smaller weight:
- A multi-host sync topology introduces a per-host configuration surface, and in
  beads' case the tool mutates part of that surface on its own. This is a cost
  of the TOPOLOGY, not of the engine - it would apply to any multi-host design
  seeds adopts, per-seed files included. It is not an argument for or against
  Dolt; it is an argument for keeping the config surface small and identical
  across hosts.
- Its failure mode was SILENT. The skipped import announced itself only under
  `bd hooks run post-merge -v`, and ~20 commits of ping-ponging counts passed
  unnoticed. Whatever seeds does here must fail loudly - which is what
  home-manager's hard-fail pre-push gate now provides.
- None of this touches the load-bearing unknown: how often does seeds'
  whole-record LWW actually drop an edit? Still unmeasured, still the number the
  engine decision should rest on, and still blocked on seeds-lcfa.1.1.
