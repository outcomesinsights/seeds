---
id: seeds-rlc2
title: "DECISION (@aguynamedryan, 2026-08-25): drop the web UI — never used, never went anywhere"
status: resolved
type: decision
created_at: 2026-08-26T03:52:21.787224+00:00
updated_at: 2026-08-31T22:40:01.494757+00:00
resolved_at: 2026-08-31T22:40:01.494751+00:00
resolution: "Executed 2026-08-31 in bead seeds-4co.8, 6 days after the ruling. Deleted: seeds serve, src/seeds/web.py, the four templates, tests/test_web.py, the Flask dependency, flake.nix's flask entry and its now-pointless pythonRelaxDeps, and the live references in README and CLAUDE.md. click is now the sole runtime dependency; the lock lost flask, werkzeug, jinja2, markupsafe, itsdangerous and blinker. Suite went 780 -> 747, which is the expected drop. Historical references were deliberately kept — CHANGELOG.md still records that seeds serve shipped, because it is git-cliff-generated history and hand-editing it would fight scripts/changelog_coverage.py. Efficacy: no tweaking; nothing outside the web UI imported seeds.web, so it was a clean severance. The lesson is about latency rather than execution — a ruling that sat unexecuted for 6 days nearly got ported onto a new storage format, and it was only caught because the storage plan enumerated what it would have to carry."
tags:
  - web-ui
  - flask
  - scope-cut
  - dependencies
  - 2026-08-25
relationships:
  - target_id: seeds-lcfa
    rel_type: relates-to
    created_at: 2026-08-26T03:52:29.225511+00:00
  - target_id: seeds-tz66
    rel_type: relates-to
    created_at: 2026-08-31T22:21:03.322211+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

@aguynamedryan, 2026-08-25, during the Dolt storage deliberation: "we can drop the webui -- that never went anywhere and I don't use it ever."

WHAT THIS REMOVES (measured 2026-08-25):
- `src/seeds/web.py` (177 lines)
- `tests/test_web.py` (398 lines, a meaningful slice of the 571-test suite)
- `src/seeds/templates/` — base.html, detail.html, list.html, questions.html
- The `serve` command in cli.py (defined around cli.py:1570, importing `seeds.web.run_server`)
- The `flask>=3.1.3` runtime dependency — which leaves `click` as the ONLY runtime dependency of the entire tool

WHY IT MATTERS BEYOND TIDINESS:
1. The runtime dependency surface drops to one package. That sharpens the distribution argument in the Dolt ledger (seeds-lcfa.3): a tool whose whole dependency list is `click` has a very high bar to clear before adding a 120 MB binary — and equally, it is very cheap to keep as Python.
2. It shrinks the port surface if a Go rewrite is entertained (seeds-lcfa.5) by ~575 lines plus templates plus an HTTP layer.
3. The global CLAUDE.md deploy note about restarting `seeds serve` processes after a deploy becomes obsolete and should go with it.
4. Fewer tests in the pre-commit/pre-push gate, which run on every commit and across four Python versions.

Check before deleting: whether anything outside this repo invokes `seeds serve` (the deploy instructions imply @aguynamedryan has run it at some point), and whether the templates hold any display logic worth preserving in the CLI's own rendering.

Not yet done — this is the captured decision, not the change. Promote to a bead before touching code.

SCHEDULED (2026-08-31): folded into the storage overhaul as a phase 5 deletion — seeds serve, src/seeds/web.py, and the four templates. The ruling was made 2026-08-25 and never executed, so all of it is still present; the overhaul would otherwise pay to port a killed feature onto a new storage format. See plans/storage-overhaul.md.
