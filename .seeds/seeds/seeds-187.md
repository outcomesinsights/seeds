---
id: seeds-187
title: "Skill: resolve-seeds-from-beads — close the loop after implementation"
status: resolved
type: idea
created_at: 2026-06-24T17:55:15.892952+00:00
updated_at: 2026-09-01T17:18:38.251603+00:00
resolved_at: 2026-08-31T21:34:46.852765+00:00
resolution: "Shipped (bead seeds-3p4) and now exercised. Efficacy: minor tweaking needed, and it was a planning-miss the seed could have caught: step 1 assumes a 'Source: seeds-NNN' lineage field on beads, and no such field exists here — the link is prose, so recovery is text-matching that over-claims. Verified against shipped code instead. What a better bead would have said: either make seeds-to-beads write a real Source field, or specify that candidates are verified against the code rather than against bead status. Second gap, worth a follow-on: the skill assumes one just-finished feature and has nothing to say about a 38-item backlog, where the work is triage. Details appended above."
tags:
  - skill
  - seeds-to-beads
  - resolution
  - efficacy
  - beads
  - winnow
  - 2026-09-01
relationships:
  - target_id: seeds-161
    rel_type: relates-to
    created_at: 2026-06-24T17:55:16.026564+00:00
  - target_id: seeds-159
    rel_type: relates-to
    created_at: 2026-06-24T17:55:16.155753+00:00
  - target_id: seeds-185
    rel_type: relates-to
    created_at: 2026-06-24T17:55:16.265161+00:00
  - target_id: seeds-152.4
    rel_type: relates-to
    created_at: 2026-06-24T17:55:16.369148+00:00
  - target_id: seeds-158
    rel_type: relates-to
    created_at: 2026-09-01T17:18:38.250786+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Proposal (drafting it now): a `resolve-seeds-from-beads` skill — the symmetric bookend to the seeds-to-beads skill (seeds-152.4). Run once, user-initiated, after an implementation session when the user is satisfied with the shipped feature.

What it does:
1. Find the originating seeds from the completed beads' "Source:" lineage (or ask).
2. Reconcile the deliberation against what actually shipped — tweaks, last-minute changes, divergences — and APPEND them to the seeds (seeds update --append, never -c which replaces), preserving the original reasoning and voice. Agent proposes; user confirms.
3. Capture the efficacy note (tweaking-needed? / planning-miss vs inherent-unknown / what a better bead would have said).
4. Resolve the seeds (children before parents).

Why it is well-motivated: it is the operational answer to two already-deferred concerns -- seeds-161 (we under-capture what we LEARNED by trying) and seeds-159 (resolved deliberation goes stale / contradicts reality). It also fixes a discoverability gap: the resolution-efficacy guidance currently lives in the seeds-to-beads skill, which fires at conversion time, but the note needs to fire at resolution time -- a dedicated resolve skill is where it actually fires. Closes the round-trip: seeds-to-beads writes lineage INTO beads; this skill reads lineage OUT to find the seeds.

Open design question (values-laden): how aggressively should the agent edit the seed record? Default chosen: append-only, preserve the original deliberation, propose-and-confirm -- never overwrite. Provenance otherwise rides on git blame (seeds-157). Relates to the still-open efficacy/metrics question seeds-185.

SHIPPED (bead seeds-3p4) — the skill exists at src/seeds/plugin/claude-plugin/skills/resolve-seeds-from-beads and installs under the seeds:* namespace. LESSON FROM THE FIRST REAL RUN (2026-08-31), which this seed's own resolution came out of: step 1 says find the originating seeds from the beads' "Source:" lineage. In this repo that lineage is not a field — it is prose mentions of seed ids inside bead descriptions, so recovering it means text-matching. That heuristic OVER-CLAIMS: seeds-lcfa.1.1 (wire seeds sync into git hooks) showed up as done because every bead mentioning it had closed, when the closed bead (seeds-ww8) had actually shipped a different, downstream fix. Every candidate has to be verified against shipped code, not against bead status. Second gap: the skill assumes one just-finished feature, and says nothing about being pointed at a backlog of 38 stale candidates, where the real work is triage — which is what happened here.



---
**2026-09-01: the two follow-ons named in this seed's resolution are now beads.**

- **seeds-20v (P1, bug)** — resolve-seeds-from-beads must verify candidates against shipped code, not bead status. Carries the seeds-lcfa.1.1 / seeds-ww8 over-claim as its worked example.
- **seeds-yd8 (P2)** — seeds-to-beads must write structured seed lineage distinguishing implemented-from-cited. Blocked on seeds-20v.

**The resolution above frames these as an either/or ("either make seeds-to-beads write a real Source field, or specify that candidates are verified against the code"). They are not.** The two fixes have different scopes: 149 beads already exist carrying prose-only lineage, and no new field can reach them, so code-verification is the only thing that repairs the existing backlog. A structured field prevents recurrence going forward. Both are needed, and 20v is the urgent half.

**The second gap this seed names is now covered elsewhere.** "The skill assumes one just-finished feature and has nothing to say about a 38-item backlog, where the work is triage" — that is `winnow` (seeds-158, beads seeds-dqu / seeds-84h), not a change to this skill. Backlog triage over the corpus is a different operation from closing the loop on one shipped feature, and conflating them is what made this skill feel inadequate to the task.

Worth noting the pattern: the over-claim recorded here is the same failure class `winnow` is explicitly designed against — a detector that reports work as done when it is not, silently, in the tool responsible for keeping the corpus honest.
