---
id: seeds-110
title: Can we tighten licensing later if we start with MIT? What are the implications for outside contributions?
status: resolved
type: question
created_at: 2026-02-27T15:43:30.408766+00:00
updated_at: 2026-02-27T15:43:30.408766+00:00
resolved_at: 2026-02-27T15:43:35.534984+00:00
relationships:
  - target_id: seeds-93
    rel_type: questions
    created_at: 2026-02-27T15:43:30.408766+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Yes, with caveats. You can release new versions under a stricter license (your own code), dual-license, or add a CLA later. But you cannot retroactively relicense others' MIT contributions without their consent. For a small/early project this is manageable — just contact each contributor. Beads also uses MIT. Strategy: start MIT, add lightweight CLA note in CONTRIBUTING.md ('by submitting a PR, you agree your contribution is licensed under MIT'), and formalize a CLA later only if the project grows enough to warrant it. The earlier you tighten, the fewer people you need consent from.
