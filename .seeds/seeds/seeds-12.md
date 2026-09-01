---
id: seeds-12
title: "Beads integration: handoff from seeds to beads for implementation"
status: exploring
type: idea
created_at: 2026-01-28T05:54:12.048719+00:00
updated_at: 2026-08-31T20:02:40.695305+00:00
tags:
  - integration
  - future
relationships:
  - target_id: seeds-22
    rel_type: relates-to
    created_at: 2026-01-28T05:54:12.048719+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Content:
From discussion.md: 'My boss is thinking this would be a handoff to Beads. That seems reasonable to me, for software.'

Vision: seeds produces the deliberation and decisions, then hands off to different tools for implementation:
- Software projects: Hand off to Beads for task tracking
- RPG character development: Produce a final character document
- House projects: Links to purchase materials, checklists, artifacts

The 'fruit' from the seed would be ADRs or similar decision documents.

Long-term possibility: Integration with AI personal assistant tools.


---
**Beads v0.50-v0.56 raises an existential question (Feb 2026):**

Beads has evolved dramatically toward seeds' territory:
- **Wisps**: ephemeral, lightweight captures — sounds like `seeds jot`
- **Molecules/protos**: structured deliberation templates — sounds like seeds' domain templates idea
- **Rich relationships**: `supersedes`, `replies_to`, `duplicates` — the deliberation graph seeds envisioned
- **Messaging/threading**: first-class threaded conversations — reasoning chains
- **Metadata system**: queryable flexible fields — the `extra` field seeds wanted
- **Graph visualization**: DAG rendering in terminal/DOT/HTML

The original vision was seeds→beads handoff (deliberation→implementation). But if beads can now capture ephemeral thoughts, thread conversations, track superseding decisions, and template structured workflows... what does seeds uniquely provide?

This is no longer a "future integration" question. This is a "does seeds still have a distinct reason to exist?" question. See child seeds for exploration.

---
**Update (Feb 2026 - beta release planning):**

The seeds-to-beads conversion is now a concrete, recurring workflow. @aguynamedryan regularly takes finalized seed decisions and manually asks an agent to create beads issues from them. This ad-hoc process works but is fragile — it depends on agent context and consistency.

Formalizing this as a rigid script/command (e.g., `seeds export --to-beads` or `seeds harvest --into-beads`) would:
- Reduce agent burden (structured conversion vs free-form interpretation)
- Improve reliability (consistent mapping rules)
- Embody the deliberation→implementation handoff that seeds was designed for

@aguynamedryan's insight: 'If I can take a process that LLMs do ad hoc and turn it into an actual rigid script, my results are more reliable and the burden on the agent is reduced.'

This becomes more important as the project goes public — contributors will need a clear workflow.
