---
id: seeds-63
title: "Validation: AI follows workflow patterns when described in prompt"
status: captured
type: decision
created_at: 2026-02-06T00:09:38.081156+00:00
updated_at: 2026-02-06T00:09:44.620585+00:00
tags:
  - workflow
  - validation
  - ai-ux
relationships:
  - target_id: seeds-61
    rel_type: relates-to
    created_at: 2026-02-05T21:43:08.458592+00:00
  - target_id: seeds-62
    rel_type: relates-to
    created_at: 2026-02-05T21:43:13.399226+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

From ETL pilot: described the workflow pattern (sources → generators → mappings) to the AI agent, and it stuck to the plan using seeds throughout.

Key insight: Seeds doesn't need built-in workflow templates if the AI can be instructed on the pattern. The structure lives in the prompt/context, not the tool.

This suggests:
1. Domain-specific seeds variations might be unnecessary
2. 'Good enough' approach: describe workflow in CLAUDE.md or session context
3. Seeds stays simple/generic, workflows are emergent from AI instruction

Tradeoff: Requires AI to be disciplined. No enforcement. But apparently that works well enough in practice.
