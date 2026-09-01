---
id: seeds-147.3
title: "Lodestone, resolved: resolve the seed + promote its decision to durable context — via a 'seeds promote' verb, not a new seed type"
status: resolved
type: decision
parent: seeds-147
created_at: 2026-06-27T04:36:30.204522+00:00
updated_at: 2026-08-31T20:02:41.403989+00:00
resolved_at: 2026-08-27T13:40:29.304319+00:00
resolution: "Decision held and shipped. `seeds trellis <id> --to <file> --as \"<line>\"` is in the CLI, the `seeds:trellis` skill ships in the plugin, README documents both, and the two-way provenance link works as specified. Body says `promote` throughout — shipped as `trellis`, renamed per seeds-198; text left as the historical record. One caveat carried forward: the phrasing-discipline mitigation for seeds-147.1 is untested — no seed in this repo has been trellised yet, so seeds-147.1 stays open."
tags:
  - lodestone
  - promotion
  - durable-context
  - provenance
  - decision
  - output-mode
relationships:
  - target_id: seeds-197
    rel_type: relates-to
    created_at: 2026-07-15T21:52:07.600507+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Where the lodestone deliberation lands.** A lodestone is *not* a new status, type, flag, or relationship inside seeds — this answers seeds-148: none of the above. It is an ordinary seed that gets **resolved**, with its distilled decision **promoted into durable project context** (CLAUDE.md / AGENTS.md / README / an ADR). The "always in active consideration" job is handled by the agent runtime, which injects those files every session — a stronger, simpler mechanism than anything seeds could surface internally. This also reframes seeds-149: lodestones don't "surface from seeds" at all; they surface because they live in always-loaded context.

**Why this beats keeping the seed open — lands seeds-147.2's A/B fork on (A).** The instinct to keep a load-bearing seed open was a *workaround* for distrust that seeds keeps paying attention to resolved seeds (see seeds-147.2). Remove the distrust — carry the decision forward via promotion, and keep resolved seeds inside the audit family (seeds-159 staleness, seeds-160 did-it-pan-out, seeds-164 candidate detection) — and the need to keep it open evaporates. Resolution becomes trustworthy; the perpetually-open model (B) is unnecessary.

**The build: a `seeds promote` verb + a thin distillation prompt.** Per the skill-vs-CLI cut in seeds-152.5, promote splits cleanly:

- **CLI verb (deterministic):** write the two-way provenance link, stamp the date, resolve the seed. Testable, scriptable.
- **Thin prompt (judgment):** distill the long deliberation into one crisp, bounded principle.

It's a new **output mode** of seeds — sibling to seeds-to-beads (seeds → executable tasks); here seeds → durable principle.

**Two hard requirements:**

- **Provenance (two-way link).** The promoted entry in the durable file cites the seed ID; the resolved seed records "promoted to `<file>` on `<date>`." Keeps the principle's *why* reachable, and lets the audit family (seeds-164) find promoted decisions to re-question on a pivot — the demotion path half-asked in seeds-150. Ties into the intent/provenance thread (seeds-168, seeds-177).
- **Phrasing discipline (the seeds-147.1 mitigation).** Promotion *maximizes* the over-channeling risk: durable context is always-on and read as a hard rule — the Jigsaw 33-refactor incident in seeds-147.1 *was* a principle in durable agent context over-applied. So the verb must force a **bounded, weighted** principle ("a code set has exactly one vocabulary ID" — crisp, scoped) and resist open-ended imperatives ("respect deprecations and move forward" — the shape that detonated). Promotion is **distillation into one crisp line**, not copy-paste.

**Open (for later):** which target file, and does seeds hold an opinion? A domain/architecture pillar (code_set_catalog's one-vocab rule) reads as a *human* principle (README / ADR); an agent-behavior directive (the Jigsaw rule) reads as CLAUDE.md / AGENTS.md. Options: (a) seeds stays agnostic — "promote to wherever your durable context lives"; (b) seeds asks/classifies at promote time. Also open: does `promote` auto-resolve the seed, or is resolve a separate explicit step?

Relates to seeds-147 (original proposal), seeds-147.1 (over-channeling risk → mitigated here), seeds-147.2 (lived origin + root cause), seeds-148 / seeds-149 / seeds-150 (answered / reframed), seeds-152.5 (the skill-vs-CLI cut it relies on), seeds-152.4 + seeds-187 (sibling skills).



---

**Open forks closed (2026-07-10, planning session with @aguynamedryan).** The three "Open (for later)" questions above are now decided; the concrete build spec lives in seeds-147.4.

- **Auto-resolve: yes, with a `--no-resolve` escape.** `seeds promote` resolves the seed in the same step. Promotion *is* a form of resolution — and this seed's whole argument is that resolution becomes trustworthy precisely because the decision is carried forward into always-on durable context. `--no-resolve` covers the rare keep-deliberating case.
- **Target file: the verb stays agnostic; the skill advises.** `promote <id> --to <file> --as "<line>"` writes wherever told — deterministic, pytest-able, usable with no agent in the loop (the seeds-152.5 cut). The thin skill supplies the judgment: agent-behavior directive -> CLAUDE.md / AGENTS.md, domain/product pillar -> README. No ADR path (@aguynamedryan is not an ADR user). If filing habits change later, it is a one-line skill edit, never a binary change or re-test.
- **Back-link storage (a third fork that fell out of the "which target file" question): resolution text + a `lodestone` tag.** No schema change. Resolution records "Promoted to `<file>` on `<date>`: <principle>"; the `lodestone` tag makes promoted seeds queryable (`seeds list --tag lodestone`) so the audit family (seeds-159, seeds-160, seeds-164) can find promoted decisions to re-question on a pivot — the demotion path half-asked in seeds-150.
