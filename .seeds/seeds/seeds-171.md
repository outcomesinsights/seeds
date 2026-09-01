---
id: seeds-171
title: Do the beads generated from a seed reference the seed they came from?
status: resolved
type: question
created_at: 2026-06-15T22:02:28.042053+00:00
updated_at: 2026-06-15T22:09:06.522327+00:00
resolved_at: 2026-06-15T22:09:06.522320+00:00
relationships:
  - target_id: seeds-169
    rel_type: questions
    created_at: 2026-06-15T22:02:28.044032+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Yes. The seeds-to-beads skill mandates it — "Cite seed IDs for deliberation context the executing agent might need" — and in practice about 37 of 83 bead records in the beads export carry a numeric design-seed reference, via a conventional "Source: seeds-X, seeds-Y" line (for example a bead citing "Source: seeds-87 (Dynamic prime), seeds-142"). The two ID schemes coexist cleanly: beads use a hash suffix, design seeds use a numeric suffix, so the numeric refs inside bead bodies are genuine provenance. A few apparent refs are test fixtures rather than real links.
