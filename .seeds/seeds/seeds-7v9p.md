---
id: seeds-7v9p
title: Should tool-config-includes-store learn package.json (dependencies/devDependencies/scripts) as a config site for prettier, markdownlint and cspell? Config-less installation is the common case and the detector misses it entirely.
status: resolved
type: question
created_at: 2026-09-08T21:02:28.167541+00:00
updated_at: 2026-09-08T22:24:20.056834+00:00
resolved_at: 2026-09-08T22:24:20.056825+00:00
relationships:
  - target_id: seeds-dv6r.1
    rel_type: questions
    created_at: 2026-09-08T21:02:28.168680+00:00
---

No — and the detector should shrink rather than grow. Ruled by @aguynamedryan 2026-09-08. tool-config-includes-store exists to warn that a repo-wide tool has not been told to skip the store, but the writer fixes plus mdformat mean the store now survives formatters by construction; warning an operator to exclude it would be telling them to undo the fix. What is still worth naming is a tool that changes MEANING rather than layout — a spell-checker running with --fix, say — not every markdown formatter. Teaching it to parse package.json would spend effort widening exactly the part that is now obsolete.
