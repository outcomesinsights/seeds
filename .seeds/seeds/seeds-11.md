---
id: seeds-11
title: "Preserving deliberation: fear of AI overwriting without recording why"
status: deferred
type: concern
created_at: 2026-01-28T05:54:11.679638+00:00
updated_at: 2026-03-11T20:50:16.164672+00:00
tags:
  - philosophy
  - ai-ux
relationships:
  - target_id: seeds-116
    rel_type: relates-to
    created_at: 2026-01-28T05:54:11.679638+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

From discussion.md: 'The terrifying thing is AI seems really happy to just generate the initial document and then change it upon feedback without recording why there was a change. We are actually scared to bring feedback to AI because it's going to overwrite the original thinking.'

Current workaround: Commit early and often. But this produces history that's:
- Thorough but not accessible
- Not natively useful for AI to review
- Doesn't show the evolution of individual ideas

Core requirement: For a given idea, track how it evolved over time.
Git history is one approach (used in MVP), but may not be sufficient for full deliberation capture.
