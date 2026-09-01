---
id: seeds-70
title: Abbreviated child IDs in nested view
status: exploring
type: decision
created_at: 2026-02-06T17:38:40.626470+00:00
updated_at: 2026-02-06T17:53:47.122409+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Design choice: In nested view, show abbreviated IDs for child seeds (just '.1', '.2' etc) instead of full IDs. This keeps the ID column compact as nesting gets deeper.

**Rationale:**
- Full IDs like seed-f865.1.1 get very wide at deeper nesting
- Causes column to expand or text to wrap awkwardly
- Parent-child relationship is already visually indicated by indentation

**Implementation:**
- Parent seeds show full ID (e.g., seed-f865)
- Children show just the suffix (.1, .2, etc.)
- Full ID available on hover (title attribute)

**Questions:**
- Is this clear enough for users to understand?
- Should we show more context (e.g., last two segments) for deeply nested items?



**Update:** Implemented and tested. The abbreviated IDs work well visually. Also added subtle gray shading for child rows that gets progressively darker with depth - this makes sorting behavior clear (parents are sorted, children stay grouped).
