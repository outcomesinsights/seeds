---
id: seeds-8lxq
title: "Does a formatter belong inside render_seed_file at all? Recommendation is no — seeds should be stable under whatever the repo runs, not become the thing that flattens an unfenced block (§7: the body is verbatim, nothing is destroyed). The alternative worth building is a read-only check that flags a body which is not stable under a CommonMark round-trip."
status: resolved
type: question
created_at: 2026-09-08T21:33:55.426084+00:00
updated_at: 2026-09-08T22:07:15.460500+00:00
resolved_at: 2026-09-08T22:07:15.460492+00:00
relationships:
  - target_id: seeds-dv6r.1
    rel_type: questions
    created_at: 2026-09-08T21:33:55.427590+00:00
---

In the writer, on render — ruled by @aguynamedryan 2026-09-08, and the format-on-input alternative is withdrawn. On-render is what makes the invariant hold by construction, since a directly-edited seed file never passes an input path. Verified: all 1,324 corpus files re-rendered with the two writer fixes plus mdformat, then mdformat run over the result, 0 changed. Constraint: seeds must use mdformat's stock defaults — using number=True left 386 files churning against a default CLI run.
