---
id: seeds-n76z
title: 'Where does fencing get enforced? Not the converter — it already writes verbatim and will not run again on any store here, and the 85 bodies needing fences are in already-converted stores. The decisive constraint: once a body is stored formatted, the unformatted original is gone from the file, so NO post-hoc check can detect that formatting reshaped it. Only the writer sees both. Options: (a) format_body compares the CommonMark rendering of the incoming body against the formatted one and REFUSES on a difference, naming the fix; (b) warns and proceeds; (c) auto-fences the offending run. Recommendation is (a) plus normalize refusing, and never (c): the detector knows which BODY changes, not which LINES were meant to be literal, and wrapping indented prose in a fence is a worse and more permanent error than the collapse it prevents.'
status: resolved
type: question
created_at: 2026-09-09T14:18:34.295046+00:00
updated_at: 2026-09-09T14:32:30.609441+00:00
resolved_at: 2026-09-09T14:32:30.609434+00:00
relationships:
  - target_id: seeds-dv6r.1
    rel_type: questions
    created_at: 2026-09-09T14:18:34.296219+00:00
---

Handle it automatically, in three tiers, with no user prompt anywhere — ruled by @aguynamedryan 2026-09-09 ("agents are the only ones ever using the seeds CLI... I want these things handled rather than bothering the user"). And YES the converter needs it: two other hosts and possibly other users still have pre-0.7 stores to convert, and those bodies have never met a formatter. Tier 1, auto-fence the literal RUN inside a paragraph — not the paragraph, which would set a prose lead-in in monospace. Tier 2, where the residual is whitespace-only, format anyway: those are hanging-indent prose quotes, the words all survive, and fencing them would be the wrong answer. Tier 3, where the body would STILL be structurally reshaped, store it unformatted — lossless, silent, and check --smells names it as non-canonical-bytes so it is visible rather than hidden. Measured over 1,337 bodies: 64 auto-fenced, 51 of those then fully stable, 32 whitespace-only residual, 2 structural. The fencing is purely ADDITIVE — two fence lines, indentation kept, not one character removed — which is what lets the converter keep verifying that a pre-0.7 body landed verbatim.
