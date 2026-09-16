---
id: seeds-sx1r
title: 'Cross-family review: a Claude reviewer judging Claude is the weakest form, and the fix already ships in this ecosystem'
status: captured
type: idea
created_at: 2026-09-16T16:07:25.422633+00:00
updated_at: 2026-09-16T16:08:38.558662+00:00
tags:
  - self-preference-bias
  - cross-family
  - llm-as-judge
  - adversarial-review
  - prior-art
relationships:
  - target_id: seeds-cpkr
    rel_type: relates-to
    created_at: 2026-09-16T16:08:38.360999+00:00
---

Any design where a Claude agent reviews a Claude agent's decisions inherits
**self-preference bias**, and a second Claude reviewer barely helps: two correlated votes
are not much better than one.

The bias is documented and tied specifically to a model's ability to recognize its own
output — *Self-Preference Bias in LLM-as-a-Judge* (arXiv 2410.21819); *Justice or
Prejudice? Quantifying Biases in LLM-as-a-Judge* (ICLR 2025, IBM), which introduces CALM
and quantifies twelve bias types. Same-family judging compounds it.

**Cross-family review is the cheap structural answer**, and it already exists in this
ecosystem rather than needing to be built: second-opinion MCP servers, and the OpenAI
Codex plugin for Claude Code doing cross-provider review. The typical API is async —
`start_review` returns an id, `get_review` collects later — which suits a review that
should not block.

Where it applies here: the outside-in reviewer in \[[seeds-cpkr]\]. That role is the one
whose value comes from NOT sharing our habits, so a different model family is a strict
improvement on the same role, not a different role. The inside-out reviewer needs deep
familiarity with the repo and is a weaker candidate.

seeds-cpkr's honest list of what survives a degraded reviewer credits "two independent
reviewers — a weak vote, but better than one." This is the finding that says *how* to
make the vote less weak, and it was the largest single improvement the outside-in reviewer
identified in the 2026-09-16 run.

Not free: it introduces a second provider, a second set of credentials, and a dependency
on tooling outside the seeds package — which sits awkwardly against \[[seeds-gi9k]\]
(guidance an agent needs must ship IN the package). Optional rather than required is
probably the shape.
