---
id: seeds-x6m0
title: "Seed walkthrough format: prose context block + AskUserQuestion chips, scoped to a related set — validated on the seeds-147 cluster"
status: captured
type: decision
created_at: 2026-08-27T13:41:42.138187+00:00
updated_at: 2026-08-31T20:02:50.328200+00:00
tags:
  - ai-ux
  - walkthrough
  - review
  - askuserquestion
  - skill
  - seed-identity
  - validated
  - 2026-08-27
relationships:
  - target_id: seeds-vo56
    rel_type: relates-to
    created_at: 2026-08-27T13:41:48.728490+00:00
  - target_id: seeds-152.5
    rel_type: relates-to
    created_at: 2026-08-27T13:41:48.845665+00:00
  - target_id: seeds-147
    rel_type: relates-to
    created_at: 2026-08-27T13:41:49.018264+00:00
  - target_id: seeds-74.2.1
    rel_type: relates-to
    created_at: 2026-08-27T14:08:02.282402+00:00
  - target_id: seeds-74.2
    rel_type: relates-to
    created_at: 2026-08-27T14:08:02.392709+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**The ask (@aguynamedryan, 2026-08-27).** "When I ask 'let's walk through seeds and show me each one and ask me anything you need my input on', I'd really like it if only a single seed at a time is presented with as much context as necessary, along with questions to answer" — and: would `AskUserQuestion` be a good fit for the questions?

**Ruled: yes, but only for the ruling half.** The split that matters is **ruling vs. reasoning**.

- **Chips fit the ruling.** The per-seed disposition (resolve / defer / abandon / keep exploring / promote to a bead) is the same discrete choice asked once per seed, and questions that already enumerate their own candidates are chip-shaped by construction (seeds-148 literally listed four positions in its body).
- **Chips do not fit the reasoning.** Open questions where @aguynamedryan's argument *is* the artifact — seeds-170 ("does seeds' structure help the agent reason or fight it?"), seeds-174 ("devise a quantitative test") — must stay prose. Four invented options would anchor the answer and record a verdict while discarding the why, which inverts seeds' whole premise: the deliberation is the thing being captured, not the decision log.
- **The bridge is the `notes` annotation**, plus the always-present "Other" escape hatch: a chip for the ruling, free text for the reasoning, so the seed gets both and a badly-framed option set costs a sentence rather than a wrong answer.

## The format, as validated

1. **One seed per turn, prose context block.** `AskUserQuestion` renders no context of its own, so this half stays prose and does the heavy lifting: what the seed proposed, where the deliberation actually landed, what shipped (with commits), what is stale, and what is genuinely still unsettled — with every sibling seed ID glossed inline. This is the concrete answer to seeds-vo56 (agents cite seed IDs with no gloss and @aguynamedryan cannot follow): the walkthrough format makes the gloss structural rather than a rule to remember.
2. **Then one `AskUserQuestion` call** carrying that seed's open questions plus the disposition — up to 4 fit in a call, which comfortably covers one seed.
3. **Write the answers back, then move on.** Nothing is mutated before the answers come in.

**Previews earn their place on the disposition question.** Rendering the concrete consequence — which seed IDs get resolved, which stay open, what stays blocked — is information @aguynamedryan cannot hold in his head across four options, and the side-by-side layout makes the trade visible rather than described.

## Scope — this is NOT a standing full-database review

@aguynamedryan, explicitly: a full ~40-seed pass would be daunting. The walkthrough is for **preparation before implementing a handful of seeds**, or a **focused review of a related set**. It is not a periodic sweep of everything. Any skill built for this must therefore take a filter (a tag, a cluster, a parent, an age) rather than defaulting to `seeds ready` wholesale.

## What the trial run demonstrated (seeds-147 lodestone cluster, 2026-08-27)

Chosen because it looked like open deliberation and was not. The format surfaced three things a per-seed skim would have missed:

- **The cluster was already answered and shipped.** seeds-147.3 ruled the shape; seeds-147.4's build spec landed as `seeds trellis` (commits 6deede5, f678b29, dc8b496), renamed from `promote` per seeds-198. seeds-148 / seeds-149 / seeds-150 sat at `captured` while their answers had been on the record for weeks.
- **A structural constraint the review had to respect.** Only `resolved` and `abandoned` are terminal (`db.py:574`, `models.py:457`), so leaving one child open keeps the parent blocked and deferring does not help. Forcing full context before asking is what exposed this — it changed the option set rather than being discovered afterwards.
- **The one genuinely live item, kept live.** seeds-147.1's over-channeling risk stays open because its phrasing-discipline mitigation has never been exercised — no seed in this repo has been trellised yet. @aguynamedryan had no answer to the concern, and "no answer" was correctly recorded as *still live* rather than quietly closed.

Outcome: six seeds resolved, one deliberately left open, parent still blocked as an honest signal. @aguynamedryan on the format: "this is exactly the interaction, level of detail, and setup for input that I was hoping for."

## Where it would live

Judgment side of the seeds-152.5 cut (deterministic -> CLI verb, judgment -> thin skill), so: a thin skill over existing verbs, not a `seeds walkthrough` command. The mechanical parts it would lean on — reading a cluster, checking blocked state, writing resolutions — are already verbs.

**Not yet built.** This is the captured decision on shape and scope; promoting it to beads is a separate step.

Relates to seeds-vo56, seeds-152.5, seeds-147.

## Scoping: the skill must be context-aware (@aguynamedryan, 2026-08-27)

**The directive:** limit tending to seeds recently discussed and/or relevant to the current discussion — never the whole database. This is the enforcement mechanism for the scope constraint above; without it the skill degenerates into the ~40-seed sweep @aguynamedryan rejected.

**Finding: this needs no new CLI work.** Every retrieval verb it wants already exists — `suggest`, `tree`, `search`, `list --since/--tag`, `recent`. Per the seeds-152.5 cut this lands cleanly: retrieval is already deterministic and already in the binary, so the skill is pure judgment on top.

### Three tiers, in confidence order

1. **Named in this conversation — the spine, zero tooling.** The agent collects seed IDs that have appeared in its own context this session. Exact and free. **The database cannot supply this**: it records what was *written*, never what was *discussed*.
2. **Graph neighbors — `seeds tree <id>`, one hop.** Children, parent, `relates-to`. In the seeds-147 trial this is what made the cluster cohere; it was walked by hand and should be explicit in the skill.
3. **Topic retrieval — `seeds suggest --open-only "<the discussion topic>"`.** Catches relevant seeds nobody named. Proven in the trial: it surfaced seeds-74.2 / seeds-74.2.1, a directly-relevant design cluster that was in neither participant's context. `--open-only` is required — `suggest` includes terminal seeds by default because it was built for dedup, and tending is about open seeds.

### Explicit non-mechanism: `seeds recent` must NOT scope the tend set

It is the obvious choice and it is wrong, measured 2026-08-27:

- It sorts on `updated_at`, which records writes rather than discussion. A 2-day window returned the whole Dolt/storage cluster from 2026-08-25 — irrelevant to the conversation at hand, and numerically dominant in the results.
- **Tending itself writes.** After a tend session, `recent` returns exactly the seeds just tended. It is self-poisoning as a scoping input.
- It excludes terminal seeds by default, so six seeds resolved an hour earlier had already fallen out of the window.

`recent` keeps exactly one job: the **cold open**, where tending is invoked with no prior discussion to derive a set from. There, `recent` + `ready` is a reasonable opener — and the skill should state that this is its only sanctioned use.

### Candidate list needs a trim gate

Even a context-scoped set can overshoot. Before presenting seed #1 in full, the skill emits the candidate list with a one-line gloss each, grouped by tier, and lets @aguynamedryan trim it — a natural multiSelect `AskUserQuestion`. Full context blocks are expensive to produce and read; spend them only on seeds that survived the trim.

### Relationship to the sweep thread (seeds-74.2 / seeds-74.2.1)

**Tend is sweep's inverse, not a duplicate.** Sweep goes *conversation -> new seeds* (extraction/capture); tend goes *existing seeds -> rulings* (review/disposition). They share the conversation as scoping context and move in opposite directions.

One observation that applies to both: seeds-74.2.1 specs `seeds sweep` as a CLI command whose first two steps locate and parse the session JSONL, then ship it to Claude — machinery that exists purely to reconstruct context a **skill** already has by virtue of running inside the conversation. If sweep ever gets built, the skill form is strictly cheaper for the same reason tend's is.

### Still unruled

- **The name.** Candidates: `tend` (fits the garden family, and "you tend a bed, not the garden" carries the scope constraint), `walkthrough` (@aguynamedryan's own word, generic), `rounds` (medical rounds; best captures one-at-a-time discipline, imports an unused metaphor). Note per seeds-152.5 that auto-discovery keys off the skill `description`, not the name, so the name is for typing and for the plugin listing.
- **Cold-open behaviour.** Does an unscoped invocation fall back to `recent` + `ready`, or refuse and ask for a filter?

## Both open items ruled (@aguynamedryan, 2026-08-27)

**Name: `tend`** — surfaces as `seeds:tend`, joining `seeds:feedback` / `seeds:seeds-to-beads` / `seeds:resolve-seeds-from-beads` / `seeds:trellis`. Chosen for the garden family already established by `seeds` and `trellis`, and because the metaphor carries the scope constraint for free: you tend a bed, not the whole garden.

**Cold open: start immediately from `recent` + `ready`. No trim gate.** Invoked with nothing to scope from, the skill builds a set from the recency window and begins presenting seed #1 — it does not propose a candidate list for confirmation first, and it does not refuse and ask for a filter.

**The reasoning, which supersedes the trim-gate proposal above.** One-seat-at-a-time presentation is **interruptible by construction**: a mis-scoped set costs one seed's worth of reading and a redirect ("no, the storage ones"), not a wasted session. The trim gate was solving a problem the format already solves, and it charged friction on every single invocation to do it. Drop it — from the cold path, and from the warm path where the named-in-conversation set is precise anyway.

**Residual risk and its cheap mitigation.** The cold path is exactly the mode that surfaced the irrelevant Dolt cluster in the 2026-08-27 test. The mitigation is not a gate: state the scope in **one line** before presenting seed #1 ("12 seeds updated in the last 7 days, starting with the storage cluster"), so a wrong scope is visible and redirectable before much has been spent. Announcing is not gating.

**Held provisionally, by intent (@aguynamedryan, 2026-08-27):** "we'll attempt to use recent/ready first and see if we need to tweak that approach later." The cold-open ruling is a starting point to be revised from lived use, not a settled design — so first real tending sessions should note when the cold set was wrong and what would have scoped it better. If it needs tweaking, the one-line scope announcement is the place to start (make it richer, or let it offer a narrower cut) before reaching back for a gate that was already rejected on friction grounds.
