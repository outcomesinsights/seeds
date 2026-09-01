---
id: seeds-198
title: "Naming: parked at 'lodestone'; garden-term rename (sage/elder for a 'guiding voice') deferred"
status: resolved
type: decision
created_at: 2026-07-16T16:32:43.375225+00:00
updated_at: 2026-08-31T20:02:46.429831+00:00
resolved_at: 2026-07-16T19:43:52.181380+00:00
resolution: Chose 'trellis' — the gentle structure future work is trained along; shipped in v0.3.4
tags:
  - naming
  - lodestone
  - garden-metaphor
  - guiding-voice
  - section-heading
  - deferred
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Decided (2026-07-16): the promote verb + skill were renamed to `lodestone`**, unifying the feature on one term. The tag, the `## Lodestones` section, and the concept already said "lodestone"; only the command/skill were the odd ones out at "promote". Clean break, no alias — `seeds lodestone`, `seeds:lodestone`. "promote this" survives only as a natural-language trigger phrase in the skill description. Shipped in v0.3.4. This supersedes the *naming* half of seeds-147.3 (which coined "a `seeds promote` verb").

**Why `lodestone` "for now" rather than a garden-native term.** @aguynamedryan's instinct was sound: "lodestone" is a navigation/rock metaphor that clashes with the seeds/garden vocabulary (seeds, jot, prime, prune). We explored garden alternatives to make the theme cohere — but each fell short, and @aguynamedryan parked at lodestone to stop blocking the release. It survives because it is *agent-legible*: an agent reads "lodestone" as "guiding principle" for free (the original reason @aguynamedryan chose it).

**The garden-term exploration — deferred, genuinely worth revisiting:**
- **taproot** and **rootstock** — rejected. *Rootstock* implies **grafting** (a scion of a different variety joined on top) — the wrong mechanism. *Taproot* implies **permanence / anchoring**, but not the key quality below.
- **The sharpened criterion (@aguynamedryan):** the term should evoke an idea that is **important, enduring, AND a guiding voice** — not merely permanent. That's a "wise-elder" quality, which every permanence-word (taproot, rootstock, evergreen, perennial) misses.
- **Best garden candidates for the "guiding voice" quality:** **sage** — a sown herb *and* a source of wise, guiding counsel ("sage advice"); hits all three at once — and **elder** — the elder shrub *and* a community's respected, enduring, guiding voice. (Runners-up: *mother tree* — purest meaning but two words; *sentinel* — leans "guardian" over "counsel".)

**Section-heading decoupling (agreed, not yet needed).** If we ever adopt an *opaque* garden term, the durable file's section should stay plainly `## Principles` — a stranger reading someone's CLAUDE.md shouldn't have to decode the tool's cute name. The command can be poetic; the output stays legible. Kept `## Lodestones` for now because "lodestone" is legible enough that no gloss is required.

Relates to seeds-147.3 (the promote-verb decision, whose naming this supersedes) and seeds-197 (the prime-discovery decision). A lifecycle diagram illustrating where this sits was produced alongside this session.



---

**Horticultural sweep (2026-07-16).** Ran a four-way terminology sweep — trees/forests, root/stem morphology, symbolism/folklore, garden-design — ~50 candidates scored against *important / enduring / guiding-voice*. Full scored comparison artifact: https://claude.ai/code/artifact/ae996e82-3bae-4d1b-8e07-2d9b9a8e5610

**Genuine finalists that beat taproot/rootstock:**
- **leader** — the tree's central stem that steers all growth via apical dominance; the tightest literal fit (three of four sweeps converged on it), but reads corporate/plain.
- **hazel** — the Celtic tree of wisdom AND the forked divining rod you orient by; the freshest find — fuses "wise" with "guides" and patterns like sage/elder; the wisdom lore is a touch niche (most think hazelnut).
- **oak** — council/gospel/charter oaks, where communities gathered to decide; the most legible and warm; its "voice" comes from heritage, not mechanism.
- **linden** — the Germanic justice/council tree (binding rulings spoken *sub tilia*; "could not lie" beneath it); guiding-voice is its whole identity.
- **laurel** — the Delphic oracle's plant + the laureate's wreath (prophecy + honored authority); faint "rest on your laurels" undertone.
- (also solid: **standard** — the coppice tree left to grow on + "a norm"; **sage/elder** — the originals; **crown/veteran/olive** — good but off one axis.)

**Perfect concept, unusable word (inspiration only):** moot/trysting tree (the tree a community convened under to decide), witness/bearing tree (a durable landmark future work "takes its bearing" from — puns on load-bearing), compass plant (*Silphium*, leaves orient N–S — a literal botanical lodestone, but it *orients* rather than *counsels*, re-importing lodestone's flaw).

**Honest read:** no single word is at once maximally legible, richly evocative, all-three, AND garden-native — each finalist trades one thing. Closest to clearing the bar: **hazel** and **oak**. The field now feels genuinely exhausted; the future call is a taste pick among these finalists, not more searching.



---

**Correction (2026-07-16, per @aguynamedryan): hyphenate the compounds.** Multi-word terms are NOT disqualified — `seeds mother-tree` / `seeds compass-plant` are valid command names (cf. `git cherry-pick`). The earlier "perfect concept, unusable word" tier was miscategorized; re-judged on meaning alone:
- **mother-tree** — jumps to TOP tier: the hub tree that nurtures and "teaches" its seedlings = genuine living counsel; hits all three axes cleanly (only ding: "mother" leans nurturing-source over authority).
- **council-oak** — real contender: oak's warmth + legibility plus an explicit "the tree decisions gather around," which fixes oak's one weak axis (its voice was heritage, not mechanism).
- **compass-plant** — viable; the most literal "garden translation of lodestone," but keeps lodestone's own trait — it orients rather than counsels, and reads directional more than foundational.
- moot-tree / trysting-tree — still out, but on CONNOTATION ("moot" = irrelevant; "tryst" = romantic rendezvous), not word-count.

Revised finalist shortlist (single- and multi-word): **mother-tree, hazel, oak / council-oak, sage / elder, compass-plant, leader.**



---

**Reframe (2026-07-16, per @aguynamedryan) — name the tool that guides growth, not the promoted plant.** The key shift in the whole search: a principle isn't an important *plant* (elder / specimen / mother-tree) — it's the gentle structure future growth is *trained along*. Tone matters: seeds is gentle software; nurturing is valid, and authority is NOT the overarching idea. This moves the search onto the grower's **guiding tools/techniques**:

- **trellis** — NEW LEAD, and the best word found so far. It bears the plant's weight, endures season after season, and guides direction — *yet the plant can still grow off it*, so it encodes "weighted, not binding" (the exact seeds-147 nuance: a heavily-weighted reference point, not a hard guardrail). Gentle, legible, garden-native, works as verb and noun (`seeds trellis <id>`).
- **tuteur** — literally "tutor" (a gentle tutor of growth); perfect meaning, but an obscure French word.
- **nurse-plant** — guidance as *care* (a plant/log that fosters seedlings); the nurturing reading.
- **stake** — gentle support; some bet/claim baggage.
- **espalier** — shaped growth; obscure/hard-to-spell word.

The plant-noun picks (oak / sage / hazel / mother-tree / leader) recede under this reframe — they name an important plant, not the thing that shapes growth. **mother-tree** and **nurse-plant** stay valid if the desired flavor is *living / nurturing* rather than *structural*. Full comparison artifact (reframe-led): https://claude.ai/code/artifact/ae996e82-3bae-4d1b-8e07-2d9b9a8e5610



---

**DECIDED (2026-07-16): `trellis`.** @aguynamedryan chose it — the reframe's answer, and the best word the whole search produced. Command `seeds trellis`, skill `seeds:trellis`, tag `trellis`, section `## Trellises`; the SKILL.md and README were reframed to the train-along / gentle metaphor ("a trellis is the structure future work is trained along — weighted guidance you can still grow off of," which is exactly the seeds-147 "not a hard guardrail" intent). Ships in v0.3.4. Naming supersedes seeds-147.3's original `promote` and the interim `lodestone`. The exploration above stands as the record of how we got here (promote → lodestone → the garden-term sweep → the "name the guide, not the plant" reframe → trellis).
