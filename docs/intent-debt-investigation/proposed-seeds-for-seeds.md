# Proposed seeds for seeds

> **Status: proposed, not filed.** These are candidate seeds I (an agent, working in oimnibus) would consider adding to the **seeds** project's own deliberation backlog. Nothing here has been written to `~/projects/outins/seeds/.seeds/` — this document exists so the thinking isn't lost, and so seeds itself can later glean these, verify them against its live backlog, and draw its own conclusions (merge, refine, reject, or file).
>
> **Where they came from.** A landscape study of the early-2026 discourse on capturing intent/deliberation and the AI-recording firehose (see `capturing-the-why-landscape.md`), an evaluation of seeds against that landscape (`capturing-the-why-seeds-evaluation.md`), and a full read of all 195 seeds in the live seeds DB. After filtering out everything the backlog already covers, six gaps remained. The full reasoning — what's already covered, what I rejected — is in `seeds-gap-analysis.md`.
>
> **A note to the reviewing agent (seeds).** Treat these as candidates from an outside reader, not as decisions. Each one names what it's *distinct from* in the existing backlog so you can confirm it isn't a duplicate; verify that against the current DB (this was read 2026-06-11 at 195 seeds — the backlog may have moved). Where a candidate overlaps an existing seed, prefer updating that seed over filing a new one. The framing, types, and tags are suggestions.

---

## Proposed seed 1 — Resolved deliberation can go stale

- **Type:** concern
- **Tags:** lifecycle, decay, staleness, maintenance, intent-debt
- **Suggested links:** `relates-to` seeds-50 (coherence check), seeds-131 (re-ingestion), seeds-7 (reality-disagreed reopen)
- **Provenance:** Meta, "How Meta Used AI to Map Tribal Knowledge" (2026) — *"context that decays is worse than no context at all"*; Storey, intent-debt as *erosion* of externalized rationale.

**Proposed body:**

> seeds preserves the journey, but a resolution captured months ago rests on premises — data shape, library versions, constraints, team priorities — that may since have changed. The intro post already notes "resolved seeds occasionally get reopened because reality disagreed," but that is reactive and manual; there is no concept of a resolution *aging out*.
>
> The field names this directly. Meta's tribal-knowledge work warns that stale context is worse than none, and it re-validates its own context files on a schedule. The intent-debt framing treats externalized rationale as something that *erodes* over time, not just something present or absent.
>
> Open questions:
> - Should a resolved seed carry a light validity/confidence signal, or an optional "revisit-by" hint?
> - When a new seed brushes against an old resolution, can the agent flag "this decision's premise may no longer hold"?
> - Is staleness even detectable by the tool, or only assertable by a human revisiting?
>
> Distinct from seeds-50 (coherence of the *live* graph — story, not freshness) and seeds-131 (re-gleaning *source inputs*, not re-validating *resolutions*).
>
> Risk to weigh: seeds is journey-capture, not a freshness monitor. A lightweight "revisit" affordance may be all that fits the ethos; a decay-detection engine would over-build.

---

## Proposed seed 2 — The candor paradox (and the audit-log chilling effect)

- **Type:** concern
- **Tags:** philosophy, candor, observer-effect, privacy, positioning
- **Suggested links:** `relates-to` seeds-103 (.seeds public), seeds-127 / seeds-133 (source privacy), seeds-153 (customization drift)
- **Provenance:** a16z, "Everything Is Recorded Now" and its comment thread (*"you capture more context, but a thinner, more performed version of it"*); White & Case, "When every word is recorded" (governance/chilling).

**Proposed body:**

> The sharpest critique in the AI-recording literature is the observer effect: once people assume everything is recorded, the messy half-formed thinking that produces good decisions migrates to the unrecorded hallway. You capture more context, but a thinner, more performed version of it. Two angles bear on seeds:
>
> 1. **Performance under capture.** When the agent (or I) know a deliberation will be filed into seeds — and that `.seeds/` may be public (seeds-103) — does the thinking get quietly performed or self-censored? seeds' whole value is the *candid* journey; if capture makes the journey less candid, that's corrosive at the root.
> 2. **Audit-log discoverability.** The ETL use case turns seeds into a discoverable record downstream consumers read. A candid "we shadow-priced this" or "we don't trust column X" can resurface later, detached from the context that justified it — the governance concern White & Case raise about meeting records.
>
> The positioning upside: seeds is the *antidote* to ambient recording. It is where candid deliberation is *conducted, intentionally and in the loop*, not where it is ambiently surveilled. That is a genuine differentiator versus the always-on recorders — worth saying out loud. But seeds is not immune to its own version of the paradox, and naming the risk is part of being honest about the tool.
>
> Distinct from seeds-127 / seeds-133 (privacy/copyright of ingested *source documents*) and seeds-153 (author-customization drift). This is about the candor of the *deliberation act itself*, which no current seed addresses.

---

## Proposed seed 3 — Does seeds' structure help the agent reason, or fight it?

- **Type:** question
- **Tags:** architecture, model, agent-ux, structure
- **Suggested links:** `relates-to` seeds-42 (graph DB, deferred); seeds-16 / seeds-41 (polymorphic model, types-from-relationships)
- **Provenance:** Tim Kellogg, "Agent Memory Patterns" (2026) — *"the only structure LLMs need is tokens; they reason just fine in token space,"* knowledge-graphs/SQL flagged as bad ideas for agent memory; beads v0.50–v0.56 removing ~27k lines (SQLite backend, daemon/RPC, sync).

**Proposed body:**

> seeds' value rests on structure — lifecycle, typed relations, hierarchy, blocking. A live challenge from the agent-memory field presses on that: Kellogg argues LLMs reason natively in token space and that imposing knowledge-graph / SQL structure on agent memory fights the model rather than helping it. The lodestone project corroborates from its own experience — beads' big simplification *removed* tens of thousands of lines of structure.
>
> The sharp question seeds should answer deliberately: **which of its structure serves the human-and-history (navigating deliberation over time), and which imposes schema the agent would reason better without?** This subsumes and sharpens seeds-42, which currently asks the narrower storage question (SQLite vs graph DB) and sits deferred. The answer may not be "no graph" so much as: keep structure where it serves humans (lifecycle, blocking, the durable graph), and make the *agent-facing* surfaces — `prime`, `suggest`, gleaning output — more token-native and less schema-bound.
>
> seeds-16 and seeds-41 (everything-is-a-seed, types-inferred-from-relationships) already lean minimal-structure; this extends that instinct with outside evidence and forces a call rather than an indefinite defer.
>
> What would resolve this: a concrete position on (a) whether seeds-42's graph DB is a "no" on these grounds, and (b) whether any agent-facing surface is currently over-structured.

---

## Proposed seed 4 — Retrospective outcome: did the decision pan out?

- **Type:** idea
- **Tags:** lifecycle, outcome, retrospective, feedback-loop
- **Suggested links:** `relates-to` seeds-134 (resolution field), seeds-115 (link to experiments)
- **Provenance:** Yorick (decision-journal tool) — separates *decision quality* from *outcome luck*; the intro post's "resolved seeds occasionally reopened because reality disagreed."

**Proposed body:**

> seeds captures the resolution *at close* (seeds-134) and links experiments that *inform* a decision before it's made (seeds-115), but nothing revisits a resolved decision *afterward* to record whether it held up in production. The decision-journal field makes the point worth stealing: separate *decision quality* from *outcome luck* — a good decision can have a bad outcome and vice versa, and you only learn which by looking back. The intro post already describes this happening ad hoc ("resolved seeds occasionally get reopened because reality disagreed").
>
> Open questions:
> - A light "revisit" affordance on resolved seeds — a nudge, surfaced through the agent, to look back at a decision after some time?
> - An optional `outcome` field distinct from `resolution`? ("resolution = what we decided; outcome = how it actually turned out.")
> - Does an outcome scorecard conflict with seeds' journey-not-ledger ethos, or complete it?
>
> Keep it optional and agent-surfaced (I never run the CLI myself, so this can't depend on me remembering to revisit). Partly overlaps seeds-115, which is about experiment outcomes *before* the decision — this is the *post*-resolution, in-production variant.

---

## Proposed seed 5 — Proactive corpus extraction (reconstruct deliberation nobody captured live)

- **Type:** idea
- **Tags:** gleaning, extraction, corpus, knowledge-artifact, completeness
- **Suggested links:** `relates-to` seeds-74.2.4 (source-agnostic harvest), seeds-126 (inbox), seeds-89 / seeds-90 / seeds-91 (knowledge artifacts), seeds-60 (completeness gap), seeds-62 (templates)
- **Provenance:** Meta, "How Meta Used AI to Map Tribal Knowledge" (2026) — a 50+ agent "pre-compute engine" answering standardized questions across a 4,100-file codebase, packaged as ~1k-token "compass, not encyclopedia" context files.

**Proposed body:**

> Today's gleaning is reactive: the user places a source that already *contains* deliberation (a transcript, conversation, doc) in the inbox (seeds-126), and seeds extracts (seeds-74.2.4). Meta's pre-compute engine is a different mode: proactively sweep a *whole existing codebase or corpus* with a fleet of agents answering standardized questions — "what non-obvious patterns cause failures? what tribal knowledge is buried in comments?" — to reconstruct intent *nobody ever captured as deliberation*, packaged as compact context files.
>
> For seeds this would:
> - attack the completeness gap (seeds-60) from the other side — surface what was never considered by mining what already exists, rather than only capturing what was said out loud;
> - give the knowledge-artifact concept (seeds-89/90/91) a concrete shape *and* a generation path (the compact "compass" file);
> - extend gleaning from "ingest a deliberation source" to "reconstruct deliberation from a *non-deliberation* artifact" (raw code, configs, schemas).
>
> Standardized gleaning-question templates (cf. seeds-62, where templates were considered and parked in favor of prompt-described workflows) would make it repeatable.
>
> Open question: is reconstructed-after-the-fact deliberation second-class versus captured-live, and if so, how is it marked so a reader knows the difference?

---

## Proposed seed 6 — Adopt the "intent debt" vocabulary as positioning

- **Type:** idea
- **Tags:** positioning, framing, readme, marketing
- **Suggested links:** `relates-to` seeds-101 (competitive research deferred for beta), seeds-107 (acknowledgments)
- **Provenance:** Margaret-Anne Storey, "From Technical Debt to Cognitive and Intent Debt: Rethinking Software Health in the Age of AI" (ACM Queue / arXiv 2603.22106, out of the Thoughtworks Future-of-Software retreat, Feb 2026).

**Proposed body:**

> A peer-reviewed name now exists for seeds' reason to exist. Storey's Triple Debt Model defines *intent debt* = "the absence of externalized rationale that developers and AI agents need to work safely with code," living in artifacts — distinct from technical debt (in code) and cognitive debt (in people). That is seeds' thesis with academic backing, and it arrived *after* most of the seeds backlog was written.
>
> The intro post already nails the three-layer positioning (planning / execution / deliberation). "Intent debt" sharpens the *why now*, and the surrounding discourse is a ready-made narrative seeds can borrow:
> - capture and retrieval are cheap now (the post already says this);
> - the implicit channels that used to carry intent — readable code, hallway talk, the veteran's memory — have gone dark (Osmani's "agents don't have hallways," the death of osmosis);
> - McLuhan's "retrieval" frames the moment as software rediscovering RFCs / ADRs / IBIS, which is exactly seeds' lineage.
>
> This is low-effort, high-leverage and *not a code change*: a positioning/README note, and possibly a follow-up blog angle ("intent debt and the deliberation layer"). Formal competitive research was deferred for beta (seeds-101), but this is positioning language, not a landscape survey — a different, cheaper thing.

---

## Deliberately *not* proposed (so the boundaries are explicit)

Three things I weighed and chose to leave out, so a reviewer knows they were considered, not missed:

- **An adversarial/soundness check of a seed's reasoning** (is the rationale valid, not just coherent?) — already served, lightly, by the `feedback`/closer pattern (seeds-151.1), which is seeds' "challenge the reasoning" mechanism. A heavier verifier would fight the low-friction ethos.
- **A value/ROI proof beyond capture-rate** — partly seeds-113 (gold-standard capture testing), and the intro post's deliberate "I cannot quantify any of this; it's vibes" is a *position*, not an unaddressed gap.
- **Cross-project / longitudinal deliberation** — real, but the intro post frames it as aspirational future work, and the capture trio (seeds-156) already assigns the global/passive role to clancey. A known direction, not a missing one.

## Companion documents

- `capturing-the-why-landscape.md` — the field/landscape this all came from (pure reference).
- `capturing-the-why-seeds-evaluation.md` — seeds evaluated against that landscape.
- `seeds-gap-analysis.md` — the full gap reasoning, including the already-covered map.
