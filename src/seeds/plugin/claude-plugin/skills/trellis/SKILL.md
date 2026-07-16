---
name: trellis
description: Use when the user wants to turn a matured seed into a trellis — a durable principle future work is trained along (e.g. "trellis this", "make this a trellis", "this should guide future work"). Distills the deliberation into one crisp, bounded, weighted principle and writes it into always-on project context (CLAUDE.md / AGENTS.md / README) via `seeds trellis`.
---

# Turn a seed into a trellis

The user has a seed whose deliberation has settled into a load-bearing principle worth keeping in front of future work. In the garden metaphor that principle is a **trellis** — the structure future growth is *trained along*: gentle, weighted guidance the work can still grow off of, not a hard cage. Mechanically it's an ordinary seed that gets **resolved**, its decision **distilled into one crisp line and written into durable project context** — which the agent runtime injects every session, so it shapes what grows next without anyone re-explaining it.

Do this once, when invoked. Do not adopt this as default behavior for later turns.

## Steps

1. **Absorb the deliberation.** `seeds show <id>` and walk its thread (parents, children, related) so the principle you write reflects the whole reasoning, not just the title.

2. **Distill to ONE crisp, bounded principle.** This is the load-bearing judgment and the reason this is a skill, not just a command. The principle must be *bounded and scoped*, never an open-ended imperative:
   - GOOD (bounded, scoped): "a code set has exactly one vocabulary ID."
   - BAD (open-ended, detonates): "respect deprecations and move forward."

   Why it matters: although a trellis is *meant* as weighted guidance, anything in always-on agent context tends to get read as a hard rule. An open-ended imperative once led an agent to strip 33 function instances across a codebase during a routine upgrade because a changelog gave off "deprecated vibes" — the principle had become a trigger. So keep the line *bounded and scoped* — it should guide growth, not detonate. Making a trellis is *distillation into one weighted line*, not a copy-paste of the deliberation. Propose the line and get the user's confirmation before writing.

3. **Advise the target file.** Where durable context lives:
   - Agent-behavior directive -> `CLAUDE.md` / `AGENTS.md`.
   - Domain / product pillar -> `README` (or wherever the project keeps durable prose).

   Propose the target; let the user override.

4. **Record it.** Run:

       seeds trellis <id> --to <file> --as "<the one-line principle>"

   This appends a provenance-stamped bullet to the file, records the back-link on the seed (resolution text + a `trellis` tag), and resolves the seed. Pass `--no-resolve` only if the user wants to keep deliberating.

5. **Confirm both ends of the two-way link landed** — the bullet in `<file>` cites the seed ID; the resolved seed's resolution names the file.
