---
id: seeds-93
title: Ship public beta of seeds on GitHub
status: resolved
type: decision
created_at: 2026-02-27T15:06:54.268062+00:00
updated_at: 2026-08-31T20:02:47.046640+00:00
resolved_at: 2026-03-20T20:10:26.001839+00:00
tags:
  - release
  - beta
  - publishing
relationships:
  - target_id: seeds-94
    rel_type: questioned-by
    created_at: 2026-02-27T15:06:58.659668+00:00
  - target_id: seeds-95
    rel_type: questioned-by
    created_at: 2026-02-27T15:06:59.734749+00:00
  - target_id: seeds-96
    rel_type: questioned-by
    created_at: 2026-02-27T15:07:00.529920+00:00
  - target_id: seeds-97
    rel_type: questioned-by
    created_at: 2026-02-27T15:07:01.475127+00:00
  - target_id: seeds-98
    rel_type: questioned-by
    created_at: 2026-02-27T15:07:02.104087+00:00
  - target_id: seeds-99
    rel_type: questioned-by
    created_at: 2026-02-27T15:07:03.178093+00:00
  - target_id: seeds-100
    rel_type: questioned-by
    created_at: 2026-02-27T15:19:26.347343+00:00
  - target_id: seeds-101
    rel_type: questioned-by
    created_at: 2026-02-27T15:19:28.095414+00:00
  - target_id: seeds-102
    rel_type: questioned-by
    created_at: 2026-02-27T15:21:15.446445+00:00
  - target_id: seeds-103
    rel_type: questioned-by
    created_at: 2026-02-27T15:21:15.530346+00:00
  - target_id: seeds-104
    rel_type: questioned-by
    created_at: 2026-02-27T15:21:15.620619+00:00
  - target_id: seeds-105
    rel_type: questioned-by
    created_at: 2026-02-27T15:21:15.722908+00:00
  - target_id: seeds-106
    rel_type: questioned-by
    created_at: 2026-02-27T15:21:15.850770+00:00
  - target_id: seeds-107
    rel_type: questioned-by
    created_at: 2026-02-27T15:28:34.123205+00:00
  - target_id: seeds-108
    rel_type: questioned-by
    created_at: 2026-02-27T15:39:27.599167+00:00
  - target_id: seeds-109
    rel_type: questioned-by
    created_at: 2026-02-27T15:39:28.406153+00:00
  - target_id: seeds-110
    rel_type: questioned-by
    created_at: 2026-02-27T15:43:30.408766+00:00
  - target_id: seeds-111
    rel_type: questioned-by
    created_at: 2026-02-27T15:51:28.123246+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Deliberation about best practices for publishing seeds as a public Python project on GitHub under the Outcomes Insights org (outcomesinsights). Covers licensing, packaging metadata, README, CI/CD, and release strategy.

---
**Key constraint (Feb 2026):** License (MIT) is pending employer approval since seeds was developed on work time/equipment. Phase 5 (create GitHub repo, push) is BLOCKED until licensing is resolved. All other phases can proceed.

**Repo ownership decision:** Repo will live under outcomesinsights GitHub org, not aguynamedryan personal account. Development was sponsored by OI. @aguynamedryan's attribution is in commit history. Can fork if needed (unlikely).

**Phase ordering decision:** Documentation (README, CHANGELOG) comes BEFORE CI/CD setup, not after. Rationale: want the repo presentable before wiring up automation.

**Quality bar:** CI must be tight enough to support Dependabot auto-merge with confidence. Pre-commit hooks must prevent broken commits locally. Test coverage gaps must be identified and filled before going public.

**License strategy:** MIT (matches beads). Lightweight CLA via CONTRIBUTING.md for now. Can formalize CLA or tighten license later while contributor pool is small.
