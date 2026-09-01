---
id: seeds-138
title: Can Claude Code's tool-output fold threshold be configured (globally or per-command)?
status: resolved
type: exploration
created_at: 2026-05-01T18:02:05.013947+00:00
updated_at: 2026-05-01T18:02:20.781803+00:00
resolved_at: 2026-05-01T18:02:20.781796+00:00
resolution: Claude Code does not expose a fold-limit configuration as of investigation date — no global setting, no per-command override, no always-expand marker. Our temp-file workaround (--output-file + prime.py protocol) is the documented path. Decision-making about how to refine seeds' own approach (remove --output-file? add --short mode?) stays inside seeds-137's open follow-ups. Filing /feedback in Claude Code is a possible side action, not a blocker.
tags:
  - claude-code
  - output
  - ux
  - fold-limit
  - upstream-constraint
  - workaround-revisit
relationships:
  - target_id: seeds-137
    rel_type: relates-to
    created_at: 2026-05-01T18:02:15.922050+00:00
  - target_id: seeds-31
    rel_type: relates-to
    created_at: 2026-05-01T18:02:16.016065+00:00
  - target_id: seeds-31.1
    rel_type: relates-to
    created_at: 2026-05-01T18:02:16.108420+00:00
  - target_id: seeds-92
    rel_type: relates-to
    created_at: 2026-05-01T18:02:16.208069+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Question
--------

Claude Code folds long tool output (Bash, Read) so the user has to hit
Ctrl+O to expand it. Is there a way to:

1. Raise or disable the fold threshold globally?
2. Configure it per-command or per-tool?
3. Mark certain output as "always show in full"?

Why it matters
--------------

'seeds show' produces 40-70 lines of output, which routinely crosses the
fold threshold. We currently work around it via the '--output-file' flag
(seeds-31.1) which writes to a temp file and prints the path; the agent
reads the temp file and pastes content via the prime.py protocol. If
Claude Code exposed a fold-limit knob, we could simplify or retire that
workaround.

This question is downstream of seeds-137 — once we knew bd has no
special rendering technique, the next question is whether the
constraint can be tuned upstream in Claude Code itself.

Findings (as of investigation)
------------------------------

- **No built-in fold-limit configuration exists.** No settings.json
  key, environment variable, or CLI flag controls the fold threshold.
- **No per-command or per-tool override.** Folding applies uniformly
  across all Bash and Read tool output.
- **No "always expand" marker.** No mechanism to flag specific output
  for full display.
- **Closest paths today:**
  - Redirect to temp file + Read (what we already do).
  - Break output into smaller chunks below the threshold.
  - Hook-based output post-processing (not officially documented).
  - File a feature request via '/feedback' in Claude Code.

Implications for seeds
----------------------

- The current '--output-file' workaround IS the documented path; it
  isn't going away via upstream improvement in the near term.
- The two open follow-ups from seeds-137 (remove '--output-file'? add
  a '--short' compact mode?) become more important as our only levers.
- Filing a '/feedback' request to Claude Code might be worth doing,
  but it shouldn't gate any seeds-side work.

Related: seeds-137 (parent investigation), seeds-31 (original bug),
seeds-31.1 (--output-file workaround), seeds-92 (mani fold workarounds).
