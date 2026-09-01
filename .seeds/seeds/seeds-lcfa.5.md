---
id: seeds-lcfa.5
title: A Go rewrite is the only path to embedded Dolt — but it internalizes the 120 MB rather than avoiding it
status: captured
type: exploration
parent: seeds-lcfa
created_at: 2026-08-26T03:52:09.341548+00:00
updated_at: 2026-08-26T03:52:09.341548+00:00
tags:
  - go
  - rewrite
  - dolt
  - embedded
  - distribution
  - measured
  - 2026-08-25
relationships:
  - target_id: seeds-d18f
    rel_type: relates-to
    created_at: 2026-08-26T04:03:23.758121+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Asked what a Go rewrite would change. It changes exactly one thing decisively — the process model — and it does NOT make the size problem go away.

THE MEASUREMENT THAT SETTLES THE SIZE QUESTION (titan, 2026-08-25):
The real `bd` binary (behind the nix wrapper) is 137 MB, and `strings` finds 16,695 references to `dolthub/dolt` in it. Beads really does link Dolt in-process, and 137 MB is what that costs. The standalone dolt binary is 120 MB. So a Go rewrite does not dodge the 120 MB — it absorbs it. What you trade is "the user must install a 120 MB binary on PATH" for "our tool IS a 137 MB binary." That is arguably a better trade — one artifact, no PATH dependency, no server lifecycle, no version skew between our tool and theirs — but nobody should sell the rewrite as making the tool lighter.

WHAT THE REWRITE GENUINELY FIXES — the entire cost 2 of the ledger (seeds-lcfa.3):
- In-process Dolt. No `dolt sql-server`, no port, no lock, no MySQL driver, and crucially not the shared-server mode beads tried and retired.
- No ~90 ms per-query shell-out.
- CLI latency improves independently of Dolt: `seeds show` is 113 ms today and most of that is Python interpreter startup. A Go binary starts in single-digit ms.
- The test suite stops being a hostage. 571 tests currently run in 16.1 s on ephemeral SQLite; Go tests against an in-process engine stay in that range instead of degrading to minutes. That matters because pytest runs in pre-commit on every commit and across four Python versions at pre-push.

WHAT IT COSTS:
- The port itself: 4,818 lines of `src/seeds/`, 7,433 lines of tests, 29 CLI commands. Dropping the web UI (decided 2026-08-25) removes ~575 of those lines plus four templates plus the HTTP layer, and takes `flask` with it — leaving `click` as the only runtime dependency, which is itself a reason the Python version is cheap to keep.
- Worth stating plainly given who writes the code here: agents write it, the 571 tests ARE the specification, and a repo of agent-written code is far cheaper to regenerate than the word "rewrite" implies. The honest risk is not typing effort — it is that the tests encode invariants nobody restates (the divergence guard, the future-timestamp tolerance, whole-record LWW semantics, the prose-reference allowlist, hierarchical ID rules) and a port silently drops the ones no test pins down.
- Distribution flips from `uv tool install seeds` (a small pure-Python wheel) to a 137 MB release artifact. For a public MIT tool at Beta, that changes who tries it. nix packages it either way.
- Contributor bar: Python is a lower barrier than Go for a public deliberation tool. Weak argument, but not zero.

THE STRATEGIC QUESTION THE REWRITE ACTUALLY RAISES:
If seeds becomes Go plus embedded Dolt plus a git-tracked JSONL export plus git hooks, it is architecturally the same program as beads with a different data model on top. Confront that head-on rather than discovering it later: should the two share a storage layer, or become one engine with two front doors? Answering it BEFORE a rewrite is cheap; answering it after means two Go codebases to reconcile.

VERDICT: the rewrite is the only honest route to embedded Dolt, and it is a large lever pulled for one capability. It is justified only if the FULL Dolt package — branches, cell-level merge, SQL-queryable history — is meant to be central to what seeds IS, not merely the fix for the cross-host sync pain in seeds-lcfa.1. If the goal is conflict-correct merge, seeds-lcfa.4 gets most of it without leaving Python, and option C there gets the history win too.
