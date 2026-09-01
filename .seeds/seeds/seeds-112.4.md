---
id: seeds-112.4
title: Seeds-native nudge triggers — why Clancey's commit-watcher doesn't port directly
status: captured
type: exploration
parent: seeds-112
created_at: 2026-06-05T17:25:33.361208+00:00
updated_at: 2026-06-05T17:25:33.361215+00:00
tags:
  - capture-gap
  - hooks
  - triggers
  - ai-ux
  - clancey
  - deliberation
relationships:
  - target_id: seeds-112.3
    rel_type: relates-to
    created_at: 2026-06-05T17:26:20.206670+00:00
  - target_id: seeds-141
    rel_type: relates-to
    created_at: 2026-06-05T17:26:20.343026+00:00
  - target_id: seeds-142
    rel_type: relates-to
    created_at: 2026-06-05T17:26:20.473018+00:00
  - target_id: seeds-156
    rel_type: relates-to
    created_at: 2026-06-05T17:26:20.592761+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Synthesized from a Clancey architecture deep-dive (2026-06-05). seeds-112.3 wished for a structural trigger that detects "you just discussed an open question and didn't record it." Clancey built exactly this for its own decision capture — but a naive port fails, and understanding *why* defines the design space.

**The crux: Clancey's decision points are shell-detectable; seeds' are not.**
Clancey's just-in-time nudge works by regex-scanning Bash commands in a PostToolUse hook for high-signal moments (git commit, gh pr create, git push) and firing "capture the rationale now while it's fresh." That works because a commit IS the decision point. Seeds' decision points — an open question raised in prose, a decision reversed mid-session, the user pushing back — happen in *conversation* and leave no PostToolUse footprint. A commit-watcher captures nothing seeds cares about.

**Implication: seeds needs the same two-pronged capture Clancey has, but the "live" prong fires on different triggers.**

Live prong — triggers seeds CAN hook (tool-visible):
- Seeds' own lifecycle commands (resolve / explore / abandon). A resolve means a rationale just crystallized — nudge to capture the *why*, not merely flip status.
- AskUserQuestion (a real Claude Code tool, so PostToolUse-matchable): "the user just chose X — record why." Makes seeds-141 concrete.
- A Stop / SessionEnd sweep: "did an open question surface this turn that isn't in seeds?" — the "question sweep at natural breakpoints" mused in seeds-112.3.

Retrospective prong — the case seeds CANNOT cheaply trigger (pure-conversation deliberation, no tool call): handled by transcript-incorporation gleaning (seeds-142). Clancey also pairs live nudges with a retrospective import; seeds should too.

**Empirical backing (Clancey v1.5.0):** event-tied JIT nudges "land far more reliably than generic throttled ones, while firing on every tool call only causes reminder fatigue." That is the evidence behind seeds-112.1 (prime text is the weak form) and seeds-112.2 (capture friction agents skip): a standing instruction in prime is weak; an event-tied nudge is strong.

**Policy guardrail (keep seeds deliberate):** a seeds nudge should *suggest* ("want to capture this?"), never silently auto-file. Clancey is invisible + copious by design; seeds is visible + curated. Steal the mechanism, keep the policy. See seeds-156.
