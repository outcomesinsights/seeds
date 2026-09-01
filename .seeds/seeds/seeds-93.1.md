---
id: seeds-93.1
title: "Pre-commit hooks: lint, format, and full test suite before every commit"
status: resolved
type: decision
parent: seeds-93
created_at: 2026-02-27T15:35:03.879584+00:00
updated_at: 2026-08-31T20:02:47.164513+00:00
resolved_at: 2026-03-20T20:10:20.238553+00:00
tags:
  - release
  - beta
  - quality
  - hooks
converted_at: 2026-09-01T05:20:22.746832+00:00
---

@aguynamedryan hates breaking the build. Before going public, set up pre-commit hooks that run:
- Ruff lint check
- Ruff format check
- Full pytest suite

IMPORTANT: Beads already has a pre-commit hook installed (core.hooksPath set to .beads/hooks/). This needs to be handled — see CLAUDE.md for the integration pattern (symlink beads hooks into .git/hooks/, unset core.hooksPath, use pre-commit framework with beads as a local hook).

Sibling project directories have examples of @aguynamedryan's preferred pre-commit setup. Check those for conventions.
