---
id: seeds-152.5
title: "Proposed (awaiting discussion): should seeds skills be CLI commands? The cut is deterministic→verb, judgment→thin skill"
status: captured
type: idea
parent: seeds-152
created_at: 2026-06-27T04:36:21.156430+00:00
updated_at: 2026-08-31T20:02:41.519172+00:00
tags:
  - skill
  - cli
  - command
  - architecture
  - prompt-macro
  - plugin
relationships:
  - target_id: seeds-x6m0
    rel_type: relates-to
    created_at: 2026-08-27T13:41:48.845665+00:00
  - target_id: seeds-bp0s
    rel_type: relates-to
    created_at: 2026-08-28T17:57:44.097380+00:00
  - target_id: seeds-sdhc.5
    rel_type: relates-to
    created_at: 2026-08-31T20:09:49.064092+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**The question (@aguynamedryan, 2026-06-26): should the seeds skills be CLI commands instead?** This is a proposed answer — captured for later discussion, not yet ratified.

**Proposed test — one line:** does the step need the model's judgment?

- **No → CLI verb.** Deterministic data ops belong in the binary: `resolve`, `link`, the provenance bookkeeping of a `promote` command, "emit these seeds in bead-ready shape." These get pytest coverage, are scriptable, and are usable by a human with no agent in the loop.
- **Yes → stays a skill.** Conversation-shaping and language judgment: the feedback dynamic, deciding which seeds are bead-ready, distilling a deliberation into one crisp principle, reconciling shipped-vs-intended.

**Per existing skill:**

- **feedback** — pure conversational dynamic, no deterministic content. Stays a skill; converting it buys nothing.
- **seeds-to-beads** (seeds-152.4) — hybrid: decomposition judgment stays a skill; any mechanical read/emit substep becomes a verb the skill calls.
- **resolve-seeds-from-beads** (seeds-187) — hybrid: reconciliation/efficacy = skill; the resolve + write-back = verbs (some already exist).
- **promote decision** (the lodestone thread, seeds-147) — cleanest split: a `seeds promote` verb (write the two-way link, stamp the date, resolve) + a thin distillation prompt for the phrasing.

**What this really is:** the *enforcement mechanism* for seeds-152.2 ("skills are prompt-macro scale, not workflow engines"). 152.2 said skills should stay thin but not how. The how: anything deterministic inside a skill is a smell — extract it to a CLI verb. A skill ends up thin *because* its mechanical core moved into the binary.

**Two caveats against going all-CLI:**

- **Auto-discovery is a skill-only feature.** The harness matches a skill's `description` to user intent ("treat this as feedback" → the skill fires); a bare CLI verb can't advertise *when* to use it. So the agent-facing entry stays a thin skill; logic lives in verbs underneath. This demotes the plugin (seeds-152.3) to thin wrappers over the CLI rather than the home of the logic.
- **The boundary is already flexible.** `seeds prime` is a CLI command whose output *is* a prompt — so prompt-ish things *can* live in the CLI when worth it. But `prime` injects context; it isn't an interactive dynamic like feedback, so it doesn't fully generalize.

**Open fork (for the later discussion):**

- **(P2) Keep thin skills + harden cores** — agent-facing skills stay (for discovery + fast iteration), every deterministic substep becomes a tested `seeds` verb the skill calls. (My lean.)
- **(P1) Collapse into the CLI** — even the prompt-emitters become `prime`-style verbs, drop the plugin entirely. More unified surface, but loses auto-discovery unless wrapper skills are kept anyway.

Relates to seeds-152.2, seeds-152.3, seeds-152.4, seeds-187, seeds-147.1.
