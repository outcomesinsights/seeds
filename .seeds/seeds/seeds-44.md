---
id: seeds-44
title: What is the exact relationship name between an option and its topic? ('proposed for'? 'option for'? 'candidate for'?)
status: resolved
type: question
created_at: 2026-01-28T20:53:13.870179+00:00
updated_at: 2026-01-28T20:53:13.870179+00:00
resolved_at: 2026-03-12T14:25:18.837713+00:00
relationships:
  - target_id: seeds-9
    rel_type: questions
    created_at: 2026-01-28T20:53:13.870179+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Relationship names carry the semantics. A question is just a seed with a 'questions' relationship to another seed. An answer is a seed with an 'answers' relationship to the question-seed. This keeps the model flat and polymorphic — specialize later if needed.
