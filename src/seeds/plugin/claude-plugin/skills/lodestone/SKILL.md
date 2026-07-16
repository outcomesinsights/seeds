---
name: lodestone
description: Use when the user wants to promote a seed to a lodestone (e.g. "promote this", "make this a lodestone") — distills a matured deliberation into one crisp, bounded, load-bearing principle and writes it into durable, always-on project context (CLAUDE.md / AGENTS.md / README) via `seeds lodestone`.
---

# Make a seed a lodestone

The user has a seed whose deliberation has settled into a load-bearing principle — a "lodestone" — that future work in this project should be steered by. A lodestone is not a new kind of seed; it is an ordinary seed that gets **resolved** with its decision **distilled into one crisp line and written into durable project context**. The always-in-front-of-the-agent job is handled by the runtime injecting that file every session — not by anything seeds surfaces internally.

Do this once, when invoked. Do not adopt this as default behavior for later turns.

## Steps

1. **Absorb the deliberation.** `seeds show <id>` and walk its thread (parents, children, related) so the principle you write reflects the whole reasoning, not just the title.

2. **Distill to ONE crisp, bounded principle.** This is the load-bearing judgment and the reason this is a skill, not just a command. The principle must be *bounded and scoped*, never an open-ended imperative:
   - GOOD (bounded, scoped): "a code set has exactly one vocabulary ID."
   - BAD (open-ended, detonates): "respect deprecations and move forward."

   Why it matters: lodestone principles land in always-on agent context and are read as hard rules. An open-ended imperative once led an agent to strip 33 function instances across a codebase during a routine upgrade because a changelog gave off "deprecated vibes" — the principle had become a trigger. Making a lodestone is *distillation into one weighted line*, not a copy-paste of the deliberation. Propose the line and get the user's confirmation before writing.

3. **Advise the target file.** Where durable context lives:
   - Agent-behavior directive -> `CLAUDE.md` / `AGENTS.md`.
   - Domain / product pillar -> `README` (or wherever the project keeps durable prose).

   Propose the target; let the user override.

4. **Record it.** Run:

       seeds lodestone <id> --to <file> --as "<the one-line principle>"

   This appends a provenance-stamped bullet to the file, records the back-link on the seed (resolution text + a `lodestone` tag), and resolves the seed. Pass `--no-resolve` only if the user wants to keep deliberating.

5. **Confirm both ends of the two-way link landed** — the bullet in `<file>` cites the seed ID; the resolved seed's resolution names the file.
