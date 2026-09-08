---
id: seeds-rgt4
title: How do the 54 already-written files get renormalized across 8 repos — a shipped command (seeds check --renormalize / seeds normalize), or a documented read-and-rewrite one-liner run per repo? Nothing in the CLI rewrites files today.
status: resolved
type: question
created_at: 2026-09-08T21:02:27.955381+00:00
updated_at: 2026-09-08T21:14:11.533156+00:00
resolved_at: 2026-09-08T21:14:11.533146+00:00
relationships:
  - target_id: seeds-dv6r.1
    rel_type: questions
    created_at: 2026-09-08T21:02:27.956543+00:00
---

None needed. Old bytes still parse under the new reader — a body-less ---\n\n normalizes on read, and a double-quoted scalar is still accepted — so nothing breaks and nothing must be rewritten on a schedule. The next seeds write renders each file canonical, and a prettier run gets there by itself. The only residue is check --smells reporting non-canonical-bytes on 44 files until they are touched; one read-and-rewrite pass per repo clears that if the smells-zero baseline is worth keeping.
