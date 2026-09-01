---
id: seeds-12.3
title: "GitHub issues as a seeds source: bidirectional sync between seeds and GitHub Issues"
status: captured
type: exploration
parent: seeds-12
created_at: 2026-02-27T15:28:24.304648+00:00
updated_at: 2026-02-27T15:28:24.304653+00:00
tags:
  - github
  - integration
  - sync
  - beta
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Raised during beta release planning. GitHub issues occupy a space between seeds and beads:

- Bug reports → beads-like (actionable implementation work)
- Feature requests / discussions → seeds-like (deliberation, exploration, questions)

When seeds goes public on GitHub, people will open issues that contain deliberation content. Currently there's no way to pull that into the seeds database.

Possible directions:
- `seeds import --github-issue <url>` — pull an issue discussion into a seed
- `seeds export --github-issue <seed-id>` — turn a resolved seed into a GitHub issue for implementation
- Bidirectional sync — a seed references a GitHub issue, updates flow both ways
- Tagging/labeling convention — GitHub issue labels that indicate 'this is a seed' vs 'this is actionable'

Key insight: GitHub issues are the first external source where seeds' deliberation capture would naturally apply. This is a concrete use case for the harvest/sweep architecture (seed-4653.2.4) but scoped to a single, well-structured source.

Related questions:
- Does a GitHub issue become a seed, or does a seed reference a GitHub issue?
- What happens when a seed-issue gets resolved in seeds but the GitHub issue is still open?
- Should the JSONL export include GitHub issue references?
