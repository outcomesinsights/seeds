---
id: seeds-197
title: Should `seeds prime` advertise the output-mode workflows (promote / seeds-to-beads / resolve-from-beads)? Weigh proactive agent-awareness against the 147.1 over-promotion risk
status: resolved
type: question
created_at: 2026-07-15T21:51:22.778406+00:00
updated_at: 2026-08-31T20:02:46.307403+00:00
resolved_at: 2026-08-11T19:49:08.949170+00:00
resolution: "Shipped — but under a different name than the beads describe.\n\nVerified present today: 'seeds trellis' is in the CLI ('Record a matured seed as a trellis in durable context'), backed by src/seeds/trellis.py. The implementing beads (d13, 3p4, 435) all say 'seeds promote' and lodestone.py — neither exists; src/seeds/lodestone.py is absent. The verb and concept were renamed promote/lodestone -> trellis after those beads closed.\n\nOn the question this seed actually asked (should prime advertise the output-mode workflows?): the answer shipped as NO. Bead 435's close reason records 'prime left silent per seeds-197', so the over-promotion risk won. Documentation went to CLAUDE.md and README instead.\n\nEFFICACY: not assessed. This arc was implemented in an earlier session; retroactively grading planning I did not observe would be fabrication. Resolved on verified end-state, not on a judgement of how it got there.\n\nCarried forward: a rename after the beads close leaves the deliberation pointing at vocabulary that no longer exists. Anyone reading this seed cold would search for a 'promote' verb and find nothing. When a shipped concept is renamed, append the rename to the originating seed."
tags:
  - prime
  - discovery
  - agent-awareness
  - proactive
  - output-mode
  - over-promotion
  - promote
  - workflow-discoverability
relationships:
  - target_id: seeds-147.1
    rel_type: relates-to
    created_at: 2026-07-15T21:52:07.471922+00:00
  - target_id: seeds-147.3
    rel_type: relates-to
    created_at: 2026-07-15T21:52:07.600507+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Where this came from.** While shipping `promote` (the verb, bead seeds-d13), @aguynamedryan asked the sharp question (2026-07-15): *how will agents even know `promote` exists?* Investigation found `seeds prime` emits an "Essential Commands" block (jot/create/resolve/defer/…) but advertises **none of the output-mode workflows** — not promote, not seeds-to-beads, not resolve-seeds-from-beads. So prime has never surfaced the workflow layer at all. promote just exposed the gap.

**Keep it distinct from seeds-147.3's settled non-goal.** 147.3 said "no prime injection" — but that was about not surfacing the *promoted lodestones themselves* (durable context / CLAUDE.md carries those). It said nothing about advertising the *promote command*. This seed is the second thing: capability-discovery, not content-surfacing. Do not let the two blur.

**The reactive/proactive split — the crux.**
- The designed primary discovery path is the `seeds:promote` skill (bead seeds-3p4): the harness fires it when the *user* says "promote this to a lodestone." That is **reactive** — it presupposes the user already knows promotion exists.
- Nothing makes an agent **proactively aware** the capability exists. An agent won't volunteer "this seed feels load-bearing — want to promote it?" unless something told it promotion is a thing.

**Two audiences, two channels.**
- Agents working *on* the seeds repo get seeds' own CLAUDE.md injected → documenting promote there (bead seeds-435) gives them awareness.
- Agents using seeds *as a tool* in other projects — the primary audience — never see seeds' CLAUDE.md. Their only channels are `seeds prime` (proactive) and the installed skill (reactive). prime is silent → for tool-users there is currently **no proactive awareness at all**.

**The tension (why this isn't an automatic yes).** Advertising promote in prime is exactly what would enable useful agent-*suggested* promotion — cf. seeds-147.2, where an agent spontaneously reached for lodestone reasoning ("keep this active"). But it is also exactly the amplification seeds-147.1 warns about: agents over-act on stated capabilities (the Jigsaw-33 incident; seeds-151's "context as gospel"). Tell every agent "you can promote seeds to lodestones" and some will promote too eagerly, manufacturing spurious lodestones that then sit in always-on durable context. Proactive awareness is double-edged.

**The decision to make.**
- (A) Add the output-mode workflows to prime's command list — proactive awareness for tool-users. Optionally with hedged framing per 147.1 ("promote sparingly; only load-bearing, bounded principles").
- (B) Keep prime silent; rely on the skill (reactive) + docs. Accept that agents won't suggest promotion unprompted.
- (C) In between — mention the workflows exist without encouraging use, or gate promote behind an explicit "only when the user names it" note.

**Generalizes beyond promote.** Whatever we decide should apply to the whole output-mode family (seeds-to-beads, resolve-seeds-from-beads) — they share the identical gap. promote is just the instance that forced the question.

Relates to seeds-147.1 (the over-promotion risk this must weigh), seeds-147.3 (the content-vs-capability distinction), seeds-147.2 (agent-suggested promotion as the upside), seeds-152.5 (reactive skill-discovery is the only path today), seeds-182 (dynamic prime for external routers — adjacent prime-surface question).



---

**DECIDED (2026-07-15, @aguynamedryan): keep prime silent — Option B, with two conditions.** `seeds prime` does NOT advertise the output-mode workflows. Discovery is handled by two other channels instead:

1. **User-facing documentation** must clearly explain the feature *exists* and *when to reach for it* — so a human learns lodestones are a thing and knows to call it out. (Rolls into the docs bead: not just a command-list entry, but a short "what a lodestone is / when to promote" explainer.)
2. **The skill auto-triggers on the keywords "promote" and "lodestone"** — so when the user says either word, `seeds:promote` fires. (Rolls into the skill bead's `description` frontmatter — both words must appear.)

**Rationale.** Keeps prime's surface minimal and sidesteps the seeds-147.1 over-promotion risk (no always-on nudge toward promoting), while still making the capability *discoverable by the human*, who then invokes it deliberately. Discovery stays **human-initiated** (docs teach it; keywords catch it), explicitly not agent-proactive — the mirror image of the seeds-147.3 mechanism, where the promoted *content* rides always-on context but the *capability* does not. Implementation tracked in the docs + skill beads; this seed resolves with the rest of the lodestone cluster (seeds-147.3 / seeds-147.4) once the feature ships.
