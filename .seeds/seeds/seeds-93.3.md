---
id: seeds-93.3
title: "Dependabot auto-merge: enable after CI is solid"
status: resolved
type: idea
parent: seeds-93
created_at: 2026-02-27T15:35:11.901784+00:00
updated_at: 2026-08-31T20:02:47.276212+00:00
resolved_at: 2026-03-20T20:10:20.499045+00:00
tags:
  - release
  - beta
  - github
  - automation
converted_at: 2026-09-01T05:20:22.746832+00:00
---

@aguynamedryan wants Dependabot auto-merge enabled on the public repo. This requires CI to be comprehensive and trustworthy — if tests pass across the Python version matrix, a dependency bump should be safe to merge automatically.

Prerequisite: comprehensive test coverage and tight CI (GitHub Actions with pytest + coverage + ruff + mypy across 3.9-3.13).

Will need .github/dependabot.yml configuration.
