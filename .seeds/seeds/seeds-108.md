---
id: seeds-108
title: Do we need a Contributor License Agreement (CLA)? If so, what's the frictionless way to do it on GitHub?
status: resolved
type: question
created_at: 2026-02-27T15:39:27.599167+00:00
updated_at: 2026-02-27T15:39:27.599167+00:00
resolved_at: 2026-02-27T15:39:47.591662+00:00
relationships:
  - target_id: seeds-93
    rel_type: questions
    created_at: 2026-02-27T15:39:27.599167+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Likely not needed for an MIT-licensed project. MIT is permissive enough that contributions are implicitly licensed under the same terms. The frictionless approach: add a note in CONTRIBUTING.md stating 'by submitting a PR, you agree your contribution is licensed under MIT.' If more formality is wanted later, CLA Assistant (GitHub App) lets contributors agree with a single PR comment. Heavy CLAs (Apache-style, corporate) are overkill here.
