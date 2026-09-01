---
id: seeds-lyej
title: "Python floor moves to 3.11: 3.10 was never a chosen target, and StrEnum has silently required 3.11 since the vocabulary was opened"
status: captured
type: decision
created_at: 2026-08-29T02:28:02.104758+00:00
updated_at: 2026-08-31T20:02:49.453961+00:00
tags:
  - python
  - versions
  - eol
  - dependencies
  - release
  - pre-flight
  - 2026-08-28
relationships:
  - target_id: seeds-1x6b
    rel_type: relates-to
    created_at: 2026-08-29T02:28:28.585699+00:00
  - target_id: seeds-ebg1
    rel_type: relates-to
    created_at: 2026-08-29T02:28:28.699948+00:00
  - target_id: seeds-sdhc
    rel_type: relates-to
    created_at: 2026-08-29T02:28:28.812679+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Ruled 2026-08-28 while pre-flighting the 0.6.0 bead chain. Implementation is bead seeds-yy7 (P0).

## What was found

`seeds doctor` and the test suite were both green, but the pre-push gate was not: `uv run mypy src/` reported **11 errors across 6 files**, every one cascading from `src/seeds/models.py:12`:

    from enum import Enum, StrEnum

`enum.StrEnum` was added in **Python 3.11**. `pyproject.toml` declares `requires-python = ">=3.10"` and the CI matrix tests `["3.10", "3.11", "3.12", "3.13"]`. So on 3.10 this is an **ImportError at startup — every command**, not a type-checker complaint. The mypy errors are only the local symptom: at `python_version = "3.10"` the checker resolves `StrEnum` to `Any`, which is why the cascade reads as `"str" has no attribute "value"` at seven `.value` accesses that are in fact fine.

Nothing caught it because the change (15d3a6c, opening the seed_type vocabulary) has never been pushed, and CI is the only thing that runs the 3.10 leg.

## Why the floor moves rather than the code

**3.10 was never chosen.** Traced through git: `1270e68` (2026-07-16) raised the floor from `>=3.9` to `>=3.10` for a purely mechanical reason — a Dependabot bump to `mypy>=2.3.0` required 3.10, which made the dev dependencies unsatisfiable against `>=3.9` and broke `uv lock`. Before that, `>=3.9` came from `uv init`'s default at project creation (`812e9f8`). No user ever asked for 3.10; it is the default floor, ratcheted once by a dependency constraint.

**The project already has a policy, recorded in that same commit:** "Python 3.9 reached end-of-life in Oct 2025, so drop it." **Python 3.10 reaches EOL in October 2026** — roughly six weeks after this decision. Applying the existing rule drops it. This is consistency, not a new position.

**3.11 is the floor the code actually requires.** The alternative — rewriting `SeedType` as `class SeedType(str, Enum)` — would work on 3.10 and satisfy mypy, and was checked to be behaviourally safe here: every `SeedType` use goes through `.value` explicitly, and the one f-string (`cli.py:587`) interpolates the plain `str` field rather than an enum member, so the `str(Member)` difference between the two constructs never surfaces. Rejected anyway, because it preserves support for a version nobody chose, weeks from EOL, at the cost of a construct the author did not reach for.

**3.13 was rejected too**, despite CLAUDE.md claiming it. It would cut 3.11 and 3.12 for no technical reason, and that `3.13+` line looks like the same species of undeliberate residue as the `>=3.10` it contradicts.

## Three sources disagreed and all three get reconciled

- `pyproject.toml`: `>=3.10`
- `README`: "3.10+"
- `CLAUDE.md`: "Python 3.13+"

Two of the three were wrong whatever floor was chosen. All move to 3.11.

## What this says about the pre-push gate

The gate did its job and nobody was there to see it. Per the CI-gates policy the contract is "if pre-push passes, CI passes" — and it has been false since 15d3a6c, silently, because the only thing that runs `mypy` is a hook on an action @aguynamedryan deliberately does not take. A red pre-push gate on an unpushed branch is invisible by construction.

Worth carrying into any future thinking about gates: **a gate wired to an action you never perform is not a gate.** The thing that surfaced this was a chain pre-flight taking a deliberate baseline, not the hook.

Relates to seeds-1x6b (the report whose fix introduced StrEnum), seeds-ebg1.
