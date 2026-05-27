---
name: seeds-to-beads
description: Use when the user has reached agreement on a feature after a deliberation captured in seeds, and wants the relevant seeds turned into a set of beads (tasks) executable by a Sonnet-based agent.
---

# Seeds → beads conversion

The user has deliberated a feature using seeds and now wants the agreed scope handed off as beads for execution by a Sonnet-based agent. Convert the relevant seeds into a set of beads following these principles:

- Separate actionable scope (decisions, agreed paths) from context (concerns, observations, refinements). Beads represent work; seeds carry the deliberation.
- Decompose into small, self-contained beads. Each bead should be doable in one focused effort.
- Pre-write content. If a bead requires a file with specific content, include the content verbatim in the bead description so the executing agent doesn't have to re-design.
- Acceptance criteria must be mechanically checkable (file exists, command exits 0, output contains string X).
- Set explicit dependencies between beads.
- Cite seed IDs for deliberation context the executing agent might need.
- After creating beads, land the plane: commit unstaged work into a clean tree.

Do this conversion once when invoked. Do not adopt the conversion behavior as a default for subsequent turns.
