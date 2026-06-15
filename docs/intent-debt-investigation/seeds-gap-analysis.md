# seeds Gap Analysis — what the landscape reveals that the backlog doesn't already hold

> Companion to [`capturing-the-why-seeds-evaluation.md`](capturing-the-why-seeds-evaluation.md) and [`capturing-the-why-landscape.md`](capturing-the-why-landscape.md). Written **2026-06-11 after reading all 195 seeds** in the live seeds DB (not just titles, not a sample). The candidate seeds below are drafted ready-to-file; nothing has been written to the seeds DB — that's your call.

## The headline finding

The seeds backlog is **remarkably complete**. After reading every seed, the uncomfortable truth is that most of what a fresh landscape survey would "recommend," you have already deliberated — often in more depth than the landscape articles do. So this document does two things: (1) it credits what's already covered, honestly, so I don't hand you ideas you've held for a year; (2) it isolates the genuinely thin spots — six of them — where the field has surfaced something the backlog does not yet have a seed for.

## What's already covered (so we don't re-file it)

| Theme the landscape pushes | Already in the backlog |
|---|---|
| Consume raw capture / glean from transcripts, email, Slack, PR, voice | seeds-4, 74.2.1–74.2.4, 125 (gleaning/threshing/winnowing), 126 (inbox), 130 (project-aware), 131 (re-ingestion), 142 (dedupe-and-create) |
| Distillation: verbose transcript ↔ lossy summary | **seeds-116** states it verbatim; 120 (granularity), 89/90/91 (knowledge artifacts) |
| Capture-in-the-moment (live vs after) | seeds-112, 112.1–112.4 (incl. clancey commit-watcher analysis), 113 (gold-standard testing), 141 (AskUserQuestion capture) |
| Completeness ("what haven't I explored?") | seeds-60, 50 (coherence check), 61/62 (ETL hierarchy, templates) |
| Typed relationships (supersedes, duplicates…) | seeds-6, 83.3, 124 (organic discovery), beads-validated |
| Spec graduation / "spec-ready" state | seeds-118, 122 |
| Multi-agent / multi-perspective critique | seeds-117, 121; the `feedback`/closer pattern (151.1, 151.2) |
| Agent memory / MCP-vs-CLI | seeds-83.1, 84, **85 (resolved: CLI+hooks beats MCP on token cost)**, 87 (dynamic prime, shipped) |
| ConPort / memory-bank distinction | seeds-83, **83.4 (decided: stores-conclusions vs tracks-journey)** |
| beads absorbing seeds | seeds-12, 12.1, 12.2 (resolved via Yegge's execution-only boundary) |
| ephemeral capture / wisps | seeds-86 |
| graph visualization | seeds-88 |
| metadata/extra field | seeds-40 (beads-validated) |
| privacy/copyright of sources | seeds-127, 132, 133; scrubbing hook 114 |
| AI-as-participant, not secretary | seeds-7, 21, 151, 151.1 |

That is most of the landscape. What follows is what's *missing*.

---

## The six gaps

Each is drafted as a candidate seed (title, type, tags, body) so you can file it verbatim if you agree, edit it, or reject it. They're ordered strongest-first.

### Gap 1 — Staleness / decay of resolved deliberation

- **Type:** concern  **Tags:** lifecycle, decay, staleness, maintenance, intent-debt

> **Resolved deliberation can go stale — nothing detects or flags decisions whose premises no longer hold.**
>
> seeds preserves the journey, but a resolution captured months ago rests on premises — data shape, library versions, constraints, team priorities — that may since have changed. The intro post notes "resolved seeds occasionally get reopened because reality disagreed," but that's reactive and manual; there's no concept of a resolution *aging out*. The field names this directly: Meta's tribal-knowledge work warns "context that decays is worse than no context at all," and the intent-debt literature (Storey) treats externalized rationale as something that *erodes*, not just something that's present or absent.
>
> Open questions: should a resolved seed carry a light validity/confidence signal or an optional "revisit-by" hint? When a new seed brushes against an old resolution, can the agent flag "this decision's premise may no longer hold"? Is staleness even detectable, or only assertable by a human revisiting?
>
> Distinct from coherence-check (seeds-50, which is about story-coherence of the live graph) and source re-ingestion (seeds-131, which re-gleans *inputs*). Risk of over-engineering: seeds is journey-capture, not a freshness monitor — a lightweight "revisit" affordance may be all that fits the ethos.

*Why it's a real gap:* the whole backlog optimizes for *capturing* the why; nothing addresses the why *going out of date*. This is the natural dark twin of "the deliberation survives."

### Gap 2 — The candor paradox (and the audit-log chilling effect)

- **Type:** concern  **Tags:** philosophy, candor, observer-effect, privacy, positioning

> **Does knowing deliberation is captured make it more performed and less candid?**
>
> The recording-firehose literature's sharpest critique (a16z "Everything Is Recorded Now," and its own comments; White & Case on governance) is the observer effect: once people assume everything is recorded, the messy half-formed thinking that produces good decisions migrates to the unrecorded hallway — "you capture more context, but a thinner, more performed version of it." Two angles for seeds:
> 1. When the agent (or I) know a deliberation will be filed into seeds — and that `.seeds/` may be public (seeds-103) — does the thinking get quietly performed or self-censored?
> 2. The ETL audit-log use case turns seeds into a discoverable record downstream consumers read. A candid "we shadow-priced this" or "we don't trust column X" could resurface detached from the context that justified it.
>
> seeds' intentional, opt-in, in-the-loop nature is the *antidote* to ambient recording — it's where candid deliberation is *conducted*, not ambiently surveilled — but it isn't immune to its own version of the paradox. Worth naming as both a positioning strength and a risk to watch.
>
> Distinct from source-document privacy (seeds-127/133, about copyright/PII in *inputs*) and customization drift (seeds-153).

*Why it's a real gap:* the backlog treats privacy as a property of ingested sources, never as a property of the deliberation act itself. The candor paradox is the most interesting idea in the recording half of the landscape and seeds has no seed for it.

### Gap 3 — Structure-vs-tokens: does the structure help the agent, or fight it?

- **Type:** question  **Tags:** architecture, model, agent-ux, structure

> **Does seeds' structured model help the agent reason, or fight the model's native token-space reasoning?**
>
> A live challenge from the agent-memory field. Tim Kellogg ("Agent Memory Patterns," 2026): "the only structure LLMs need is tokens; they reason just fine in token space" — and he flags knowledge graphs and SQL-backed models as *bad ideas* for agent memory. Corroborating evidence from the lodestone project itself: beads' v0.50–v0.56 simplification removed ~27k lines (SQLite backend, daemon/RPC, sync).
>
> seeds' value rests on structure — lifecycle, typed relations, hierarchy, blocking. The sharp question: which of that structure serves the *human-and-history* (navigating deliberation over time), and which imposes schema the *agent* would reason better without? This subsumes and sharpens seeds-42 (graph DB, deferred): the answer may not be just "no graph" but "keep structure where it serves humans; make agent-facing surfaces — prime, suggest, gleaning output — more token-native and less schema-bound." Worth a deliberate decision rather than an indefinite defer.
>
> seeds-16 and seeds-41 (polymorphic model, types-from-relationships) already lean minimal-structure; this extends that instinct with external evidence and forces the call.

*Why it's a real gap:* seeds-42 asks "SQLite vs graph DB" (a storage question). Nobody has asked the deeper "is the structure itself earning its keep for the agent" — which the whole agent-memory discourse, and beads' own retreat from structure, now presses.

### Gap 4 — Retrospective outcome: did the decision actually pan out?

- **Type:** idea  **Tags:** lifecycle, outcome, retrospective, feedback-loop

> **Revisit resolved decisions later to record whether they worked — not just what was decided.**
>
> seeds captures the resolution *at close* (seeds-134) and links experiments that *inform* a decision before it's made (seeds-115), but nothing revisits a resolved decision *afterward* to record whether it held up in production. The decision-journal field (Yorick) makes the point: separate *decision quality* from *outcome luck* — a good decision can have a bad outcome and vice versa, and you only learn by looking back. The intro post's "resolved seeds occasionally reopened because reality disagreed" is exactly this, today done ad hoc.
>
> Open questions: a light "revisit" affordance on resolved seeds? An optional `outcome` field distinct from `resolution` ("resolution = what we decided; outcome = how it turned out")? Does an outcome scorecard conflict with seeds' journey-not-ledger ethos, or complete it? Keep it optional and agent-surfaced (I never run the CLI). Partly overlaps seeds-115 (experiment outcomes *pre*-decision) — this is the *post*-resolution, in-production variant.

*Why it's a real gap:* the lifecycle ends at `resolved`/`abandoned` with a resolution string. There is no loop back from "what reality did with the decision."

### Gap 5 — Proactive corpus extraction (reconstruct deliberation nobody captured live)

- **Type:** idea  **Tags:** gleaning, extraction, corpus, knowledge-artifact, completeness

> **Glean deliberation from an existing codebase/corpus, not just from a source placed in the inbox.**
>
> Today's gleaning is reactive: the user places a source (transcript, doc, conversation) in the inbox (seeds-126) and seeds extracts (seeds-74.2.4). Meta's "pre-compute engine" (Engineering at Meta, 2026) is a different mode: proactively sweep a *whole existing codebase/corpus* with a fleet of agents answering standardized questions ("what non-obvious patterns cause failures? what tribal knowledge is buried in comments?") to reconstruct intent *nobody ever captured as deliberation*, packaged as compact "compass, not encyclopedia" context files (~1k tokens each).
>
> For seeds this would (a) attack the completeness gap (seeds-60) from the other side — surface what was never considered by mining what already exists; (b) give the knowledge-artifact concept (seeds-89/90/91) a concrete shape *and a generation path*; (c) extend gleaning from "ingest a deliberation source" to "reconstruct deliberation from a non-deliberation artifact." Standardized gleaning-question templates (cf. seeds-62) make it repeatable.
>
> Open question: is reconstructed-after-the-fact deliberation second-class versus captured-live, and how is it marked?

*Why it's a real gap:* every gleaning seed assumes a source that already *contains* deliberation (a conversation, a meeting). The Meta model — mine intent out of artifacts that were never deliberation (raw code, configs) — is a genuinely different capability the backlog doesn't have.

### Gap 6 — Adopt the "intent debt" vocabulary as positioning

- **Type:** idea  **Tags:** positioning, framing, readme, marketing

> **Adopt the Triple-Debt / "intent debt" framing as seeds' external positioning.**
>
> A peer-reviewed name now exists for seeds' reason to exist. Margaret-Anne Storey, "From Technical Debt to Cognitive and Intent Debt" (ACM Queue / arXiv 2603.22106, out of Fowler's Thoughtworks retreat, Feb 2026), defines *intent debt* = "the absence of externalized rationale that developers and AI agents need to work safely with code," living in artifacts (vs technical debt in code, cognitive debt in people). That is seeds' thesis with academic backing.
>
> The intro post already nails the three-layer (planning/execution/deliberation) positioning; "intent debt" sharpens the *why now*, and the surrounding framing is a ready-made narrative: capture and retrieval are cheap now (the post says this); the implicit channels that used to carry intent (readable code, hallway talk, the veteran's memory) have gone dark; and McLuhan's "retrieval" frames the moment as software rediscovering RFCs/ADRs/IBIS. Low-effort, high-leverage — a positioning/README note and possibly a follow-up blog angle. Not a code change.
>
> (Formal competitive research was deferred for beta — seeds-101 — but this is positioning language, not a landscape survey.)

*Why it's a real gap:* the backlog has competitor research (intent.build, ConPort) but never adopts the field's emerging vocabulary. "intent debt" is a sharper elevator pitch than anything currently in the README, and it arrived *after* most of the backlog was written.

---

## What I considered and decided is *not* a gap

In the interest of not padding: I also weighed an **adversarial/soundness check** of a seed's reasoning (is the rationale actually valid, not just coherent?) and a **value/ROI proof** beyond capture-rate. I'm leaving both out: the first is largely served already by the `feedback`/closer pattern (seeds-151.1) which is seeds' lightweight "challenge the reasoning" mechanism; the second is partly seeds-113 (gold-standard capture testing) plus the intro post's deliberate "I cannot quantify any of this — it's vibes" stance, which is a *position*, not an unaddressed gap. **Cross-project / longitudinal deliberation** is real but the post frames it as aspirational future work, and the capture trio already assigns "global/passive" to clancey — so it's a known direction, not a missing one.

## Suggested next step

If any of the six resonate, I can file them as actual seeds in `~/projects/outins/seeds/.seeds/` — most naturally as top-level seeds (Gaps 1–6), with Gap 3 possibly as a child or `relates-to` of seeds-42, and Gap 5 as `relates-to` of the gleaning cluster (seeds-74.2.4 / 89). Say which ones (or "all"), and whether you want them filed or left here as a review draft.
