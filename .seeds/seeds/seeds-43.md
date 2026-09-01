---
id: seeds-43
title: Questions should not live as prose inside seeds - they need their own status tracking
status: abandoned
type: idea
created_at: 2026-01-28T20:52:41.430039+00:00
updated_at: 2026-01-28T23:08:17.787610+00:00
resolved_at: 2026-01-28T23:08:17.787593+00:00
tags:
  - model
  - workflow
relationships:
  - target_id: seeds-33
    rel_type: relates-to
    created_at: 2026-01-28T17:30:19.866206+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Problem: Questions embedded as prose in seed content (e.g., 'Questions: 1. Are options distinct? 2. What relationship?') lose lifecycle tracking. We can't mark Q1 answered and Q2 deferred.

Solution: Questions should be:
- Formal Question objects attached via 'seeds ask' (have their own status), or  
- Their own seeds of type question, linked to parent

This likely resolves seed-8920 ('how are answers recorded?').

Abandoned: Consolidated into seed-80ba
