---
id: seeds-132
title: "Decision: user is gatekeeper for source document safety, not seeds"
status: captured
type: decision
created_at: 2026-03-12T20:02:06.749399+00:00
updated_at: 2026-03-12T20:02:06.749408+00:00
tags:
  - privacy
  - architecture
  - source-materials
  - decision
relationships:
  - target_id: seeds-4
    rel_type: relates-to
    created_at: 2026-03-12T20:04:54.632195+00:00
  - target_id: seeds-127
    rel_type: relates-to
    created_at: 2026-03-12T20:06:54.751838+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Decision:** Seeds will not implement automated privacy filtering, copyright checking, or sensitivity detection for source documents. The user is responsible for ensuring any document placed into the seeds inbox is safe to include.

**Rationale:**
- Automated detection is unreliable and gives false confidence
- The user knows their risk tolerance and legal obligations
- Premature configuration (dial-in comfort level) is complexity without proven need
- Seeds should stay focused on deliberation capture, not content moderation
- Convention over configuration: if it's in the inbox, seeds processes it

**What this means in practice:**
- Seeds provides no privacy/copyright guardrails on ingestion
- The pre-commit hook for sensitive info scanning (seed-195a) remains relevant as a safety net
- Documentation should make clear that anything in .seeds/ may become public
- Future: if demand proves it, a scrubbing/redaction step could be added, but not at launch

**This is explicitly NOT a permanent decision** — it's a "good enough for now" scoping choice. The concern (seed on privacy/copyright) remains open for future exploration.
