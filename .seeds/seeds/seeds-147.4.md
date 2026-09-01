---
id: seeds-147.4
title: "Build spec: `seeds promote` verb + distillation skill (the lodestone output mode)"
status: resolved
type: decision
parent: seeds-147
created_at: 2026-07-10T16:26:19.508813+00:00
updated_at: 2026-08-27T13:40:29.427851+00:00
resolved_at: 2026-08-27T13:40:29.427842+00:00
resolution: Build spec fully implemented (commits 6deede5, f678b29, dc8b496). Verb, skill, tests, and docs all landed; the default section heading became `## Principles` rather than the spec's `## Lodestones`, and the verb/skill were renamed `promote` -> `trellis` per seeds-198. Spec body left unedited as the historical record.
tags:
  - lodestone
  - promote
  - build-spec
  - cli-verb
  - skill
  - output-mode
  - bead-ready
converted_at: 2026-09-01T05:20:22.746832+00:00
---

The concrete, bead-ready build plan for the lodestone feature. Closes the open forks in seeds-147.3 (see its 2026-07-10 append) into an implementable spec. Two artifacts — a deterministic CLI verb + a thin distillation skill — the cleanest instance of the seeds-152.5 skill-vs-CLI cut.

## Artifact 1 — the `seeds promote` CLI verb (deterministic, pytest-covered)

Signature:

    seeds promote <id> --to <file> --as "<one-line principle>" [--no-resolve] [--section "## Lodestones"]

Behavior (all deterministic — no model judgment):

1. Load the seed; error cleanly if not found (reuse `get_seed_or_exit`).
2. Write forward-provenance into `<file>`: find-or-create a managed section (default heading `## Lodestones`, overridable with `--section`) and append a bullet:
       - <principle> — seeds-<id>, promoted <YYYY-MM-DD>
   The inline `seeds-<id>, <date>` citation is the file->seed half of the two-way link — human-readable and greppable. Create the file if absent.
3. Write back-provenance onto the seed: set `resolution` = "Promoted to `<file>` on <date> as a lodestone: <principle>", and add a `lodestone` tag (idempotent — do not duplicate if already present).
4. Resolve the seed (status=resolved, resolved_at=now_utc()) UNLESS `--no-resolve` is passed.
5. Echo a confirmation showing BOTH ends of the link (the file bullet and the seed's new resolution).

Date/time: use `models.now_utc()` exactly like `resolve`/`abandon`; render the citation date as YYYY-MM-DD.

## Artifact 2 — the distillation skill (judgment; thin prompt-macro)

Ships in the seeds plugin alongside seeds-to-beads / resolve-seeds-from-beads at `src/seeds/plugin/claude-plugin/skills/promote/SKILL.md`. Name: `promote` (surfaces as `seeds:promote`). User-initiated, run once, NOT adopted as default behavior (match the closing line of the other output-mode skills).

`description` (drives auto-discovery): "Use when a deliberation captured in seeds has matured into a load-bearing principle the user wants promoted into durable, always-on project context (CLAUDE.md / README) — distills the seed into one crisp bounded line and calls `seeds promote`."

Body responsibilities:

1. `seeds show <id>` (and walk its thread) to absorb the deliberation.
2. Distill to ONE crisp, bounded, weighted principle. Enforce the seeds-147.1 phrasing discipline EXPLICITLY: bounded and scoped ("a code set has exactly one vocabulary ID"), never an open-ended imperative ("respect deprecations and move forward" — the shape that detonated the Jigsaw 33-refactor). Propose the line; get user confirmation before writing.
3. Advise the target file — agent-behavior directive -> CLAUDE.md / AGENTS.md; domain/product pillar -> README. No ADR path. Propose, let the user override.
4. Call `seeds promote <id> --to <file> --as "<line>"` (auto-resolves by default).
5. Confirm both ends of the two-way link landed.

## Test surface (pytest, isolated SEEDS_DIR)

- Appends a provenance bullet to a fresh file, creating the `## Lodestones` section.
- Appends to an existing managed section without duplicating the header.
- Forward bullet contains the seed ID and the date (greppable).
- Sets resolution text naming the file + date.
- Adds the `lodestone` tag; a second promote does not duplicate the tag.
- Resolves the seed by default; `--no-resolve` leaves status unchanged.
- Nonexistent seed id errors cleanly (non-zero exit).
- `seeds list --tag lodestone` surfaces the promoted seed (verifies audit-family findability — add `--tag` filtering to `list` if it does not already exist).

## Docs / integration

- Register `promote` on the main Click group; confirm it appears in `seeds --help`.
- Add to the CLAUDE.md Commands block and the README command list.

## Provenance & non-goals

- Two-way link is the hard requirement (seeds-147.3): file->seed via the bullet citation, seed->file via the resolution text.
- NON-GOAL: seeds does NOT surface lodestones internally — no `seeds lodestones` view, no prime injection. The runtime injecting CLAUDE.md / README every session IS the surfacing mechanism (seeds-147.3 reframes seeds-149). The `lodestone` tag exists only for the audit family (seeds-159, seeds-160, seeds-164), not for runtime surfacing.
- Sibling output mode to seeds-to-beads (seeds-152.4) and resolve-seeds-from-beads (seeds-187).

Relates to seeds-147, seeds-147.1, seeds-147.3, seeds-152.5, seeds-152.4, seeds-187, seeds-149, seeds-159, seeds-160, seeds-164.
