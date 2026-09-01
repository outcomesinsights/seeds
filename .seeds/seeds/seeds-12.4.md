---
id: seeds-12.4
title: Formalize seeds-to-beads conversion as a repeatable command
status: captured
type: idea
parent: seeds-12
created_at: 2026-02-27T15:28:29.642049+00:00
updated_at: 2026-08-31T20:02:40.811231+00:00
tags:
  - beads
  - integration
  - workflow
  - automation
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Currently @aguynamedryan converts finalized seed decisions into beads issues ad hoc by asking an agent. This works but is inconsistent.

A formalized command would:
- Take a resolved/mature seed with answered questions
- Extract actionable items from the decisions
- Create beads issues with appropriate priority, type, and dependencies
- Link back to the source seed for traceability

Design considerations:
- Mapping rules: seed type → bead type (decision→task, concern→bug, etc.)
- What constitutes 'ready for conversion'? All questions answered? Status = resolved?
- Should it be `seeds export --to-beads` or `bd import --from-seeds`?
- Preserve the deliberation link: bead should reference the seed that spawned it

@aguynamedryan's principle: 'If I can take a process that LLMs do ad hoc and turn it into an actual rigid script, my results are more reliable and the burden on the agent is reduced.'
