---
id: seeds-114
title: Pre-commit hook to review seeds for personal/sensitive information
status: captured
type: idea
created_at: 2026-02-27T21:43:43.082251+00:00
updated_at: 2026-02-27T21:43:43.082259+00:00
tags:
  - security
  - workflow
  - future
relationships:
  - target_id: seeds-127
    rel_type: relates-to
    created_at: 2026-03-12T20:06:54.827479+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Before committing changes to .seeds/, automatically scan for personal or sensitive information that shouldn't be in a public repo. Things to check: email addresses, full names, employer names, internal project/dataset names, API keys, file paths with usernames, references to private repos. Could be a pre-commit hook, a seeds CLI command (seeds lint/seeds scrub), or both. Triggered by the experience of needing to scrub marketscan/MDCD/PROCTYP references before going public — would be better to catch these at commit time rather than doing a manual audit later.
