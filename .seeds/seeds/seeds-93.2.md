---
id: seeds-93.2
title: "Comprehensive test coverage: identify gaps and fill them before public beta"
status: resolved
type: decision
parent: seeds-93
created_at: 2026-02-27T15:35:08.420455+00:00
updated_at: 2026-03-20T20:10:20.354549+00:00
resolved_at: 2026-03-20T20:10:20.354540+00:00
tags:
  - release
  - beta
  - testing
  - coverage
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Now that the repo is going public with potential outside contributors and Dependabot auto-merge, tests need to be tight enough to catch regressions with confidence.

Approach:
1. Run code coverage immediately to establish baseline
2. Identify gaps, prioritizing the most important/critical code paths
3. Add meaningful tests (not just coverage padding) to fill those gaps
4. Don't need 100% unless it's easily and meaningfully achieved
5. Coverage should be good enough that Dependabot auto-merge PRs won't silently break things

This feeds into CI — the GitHub Actions matrix will run these tests across Python 3.9-3.13.
