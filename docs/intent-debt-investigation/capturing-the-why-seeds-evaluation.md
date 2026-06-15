# seeds Against the Landscape — A Strategic Evaluation

> **Companion to** [`capturing-the-why-landscape.md`](capturing-the-why-landscape.md). That document is the pure-landscape reference; this one is the opinionated read on it through the lens of **seeds** — Ryan's git-backed deliberation-capture tool.
>
> **Revised 2026-06-11** after a deep study of the actual seeds codebase (v0.3.2), its live deliberation database, the beads investigation, and the published intro post. The first draft was written from the README and backlog titles and got several things directionally wrong — most of all, it under-read how settled seeds' identity already is. Where I cite a `seeds-NN`, it's a real item in seeds' own `.seeds/` deliberation log.

---

## What seeds actually is (so the rest of this is grounded)

seeds is a small, working CLI tool (v0.3.2, public beta, MIT, ~76/78 of its own implementation beads closed). It is not a sketch — it has five months of daily use across a dozen projects behind it. Three things about it have to be understood before any "learn from / could-replace" judgment means anything:

**1. It was born from a specific fear, and against a specific alternative.** Plan files destroy evidence. Ryan's words from the founding brainstorm: *"AI seems really happy to just generate the initial document and then change it upon feedback without recording why there was a change… we are actually scared to bring feedback to AI because it's going to overwrite the original thinking."* seeds is the place where the *journey* survives the next rewrite. Crucially, he **explicitly rejected ADRs** as the answer: *"We are not interested in ADRs… ADRs capture the decision after it's made, only one step removed from a plan file."* The good stuff lives in *"hour-long conversations that weren't reviews of decisions but deep dives into the problem domain — the messy, almost philosophical, in-the-weeds part."* This matters enormously for the recommendations below: **anything that nudges seeds toward "produce a clean conclusion artifact" is pushing against the reason it exists.**

**2. The three-layer model is the published positioning.** From the intro post:
- **Planning tools** (OpenSpec, GitHub Spec Kit, task-master) — produce a spec/PRD/task-list.
- **Execution tools** (beads) — track what's being built *now*.
- **Deliberation tools** (seeds) — capture the reasoning that decides whether something becomes plannable *in the first place*.

Ryan reads Yegge's *"everyone is focused on making planning tools, and Beads is an execution tool"* and *"finished issues and future issues don't really belong in Beads — keep them in a separate store"* as **agreement** that fences off seeds' niche. The real workflow is **seeds → beads directly** ("make some beads out of these seeds"); planning/SDD tools are an acknowledged but separate bucket, *not* something seeds is trying to become.

**3. The agent is the only interface.** *"I have never personally invoked the seeds CLI. Not once… The interface is for the agent. The agent is the interface for me."* Every command is flag-based, atomic, non-interactive — built to be wielded by an agent mid-conversation, not driven by a human at a terminal. **This rules out a whole class of recommendation** (human dashboards, review UIs, manual hygiene rituals). The web UI exists but is incidental; nudges have to reach the human *through the agent*.

**What's actually built** (so I stop recommending things that exist): the full lifecycle (`captured → exploring → resolved/abandoned/deferred`), first-class question-seeds with blocking semantics, hierarchical IDs, **a discrete `resolution` field** (`resolve --resolution` / `abandon --reason`, seeds-134), **FTS5 `search` + a `suggest` dedup query** (seeds-83.2), `recent`, `doctor`, body-level seed-ID-reference validation, JSONL export, a read-only web UI, and **`prime` with a metadata-only digest** (counts, recent titles, open questions, tag clusters — bodies deliberately omitted, fetched on demand via `show`; that *is* progressive disclosure). Skills ship as **prompt-macros, not workflow engines** (seeds-152.2): `feedback` (the "closer" pattern) and `seeds-to-beads`.

**The honest limits, in Ryan's own telling:** 2 of 9 projects never used it after `init` (installing it doesn't create the habit); the **completeness gap** (seeds-60: *"lets you explore freely but doesn't tell you what you HAVEN'T explored yet"* — a forest, not a checklist); and the **capture-in-the-moment gap** (seeds-112: agents tend to capture *resolved* deliberation, not *active* deliberation; the journey is partly reconstructed from memory). Those two gaps — not "convergence," not "ADR output" — are the real frontier.

**Real usage, for texture:** marketscan_mdcd (158 seeds, 154 resolved) is the flagship — a queryable ETL *audit log* of every characterization query and compromise. code_collector spun off a 593-line `extraction_deliberation.md` companion whose ROI line is the whole pitch: *"Every hour spent on this deliberation should save 5 hours on source #10 because the questions won't need re-asking."*

## The one-line strategic read (revised)

**The field spent early 2026 catching up to a premise seeds already had, and seeds already has a clear, published answer to "why does this exist." The two risks my first draft named — drifting into spec-authoring, and accumulating instead of resolving — are largely *already guarded against*: Ryan pivoted away from ADRs on purpose, and reports "Focus" (knowing when to stop) as one of his top four surprises. The genuine open frontiers are narrower and harder: (a) capturing deliberation *as it happens* rather than after, and (b) distilling raw reasoning into something durable without making it either too verbose or too lossy — which is, almost word for word, the single biggest *unsolved* problem in the whole landscape.**

## seeds' position in one paragraph

seeds is the **IBIS / design-rationale lineage rebuilt CLI-first and agent-native**, making a bet no surveyed tool makes: that the *deliberation journey* — not the resolved decision — is the first-class artifact. It is the third leg of the **capture trio** (seeds-156): **beads** = actionable tasks (forward-looking, you-driven), **clancey** = settled facts/decisions captured passively (backward-looking, agent-serving), **seeds** = unsettled ideas you deliberately grow (forward-looking, thinker-serving). On the landscape's capture↔intent spectrum it sits at the expensive-right end (structured deliberation), exactly where the field agrees value is concentrated and tooling is thinnest.

## Verdict table

| Part II family | Could it replace seeds? | Value to seeds | The one thing to take |
|----------------|:-----------------------:|:--------------:|-----------------------|
| A. Spec-driven development | No — it's the *planning* layer, downstream | ★★★ | Keep the boundary; feed it, don't become it |
| B. ADR / IBIS / design rationale | No — it's the ancestor seeds pivoted *past* | ★★★ | IBIS options/arguments are still thin; the ADR is optional fruit, not the goal |
| C. Transcript/session capture | No — it's the raw source | ★★★★ | seeds as *consumer* of capture (the seeds-112 frontier) |
| D. Agent memory (Kellogg) | Partially (architecture challenge) | ★★★★ | Settle structure-vs-tokens for seeds-42; keep `prime` a curated block |
| E. Decision traces / context graphs | No — enterprise scale | ★★ | Stay episodic; the ConPort line is already drawn |
| F. Tacit-knowledge extraction (Meta) | No — complementary mode seeds lacks | ★★★★ | Proactive extraction as a *gleaning* mode |
| G. Harness / ticket / AGENTS.md | **Yes, the honest low-tech rival** | ★★★ | It captures the residue; seeds captures the journey it can't |
| H. PKM + the backlash | No | ★★ | The completeness gap is the real issue, not accumulation |
| **I. beads + deliberation tooling** | **Asked and answered (beads), nearest cousin (intent.build)** | ★★★★ | AI-as-participant + journey-not-destination is the moat |

The genuinely interesting "could-replace" entries are now **G** (a flat `AGENTS.md` is the real low-tech rival for "just write the why down") and **D** (Kellogg's "structure fights the model" is a live challenge to seeds' SQLite-and-relationships core). The beads question — which my first draft missed entirely — turns out to be **asked and answered**, in seeds' favor, and is worth understanding precisely.

---

## Family-by-family

### A. Spec-driven development — *a separate layer, not a gap to fill*

**Reframed.** My first draft treated SDD as "the missing layer between seed and bead" that seeds should *graduate into*. The published three-layer model is clearer: SDD tools are the **planning** bucket, a peer of beads, **downstream** of seeds and largely third-party. The May-19 `seed-vs-spec-tension` doc worried about a seed *drifting* into a 200-line spec; the June-10 post effectively **resolved** that worry not by building a spec layer but by keeping seeds purely deliberative and handing off — to beads directly, or to a planning tool if one's in play.

**Learn from.** Rickard's spec hygiene still travels well as a *handoff* discipline (declarative, layered, cheap to revise; push mechanical rules into lint/tests). CodeSpeak's **"intent recovery"** (reconstruct requirements from prior agent sessions) is a cousin of seeds' gleaning idea.

**Recommendation.** *Hold the boundary.* The right move is the discipline of **not** becoming a planning tool — resist `seeds-118/122`'s "spec-ready state" if it tempts seeds toward authoring specs. If anything graduates out of a seed, it's beads (already the workflow) or a handoff to OpenSpec/Spec Kit — never a spec seeds maintains itself. This is a *don't-build* recommendation, which is the most valuable kind here.

### B. ADR / IBIS / design rationale — *the ancestor seeds deliberately walked past*

**Major correction.** My first draft's headline move — "make ADRs the fruit; close the loop from resolved seeds to ADRs/AGENTS.md" — runs against seeds' founding thesis. Ryan **rejected ADRs on purpose**; an ADR is "one step removed from a plan file," capturing the conclusion and discarding the in-the-weeds journey that seeds exists to keep. ADR generation is real but it's `seeds-22` — *deferred*, "out of scope (future)," and explicitly *optional, domain-specific fruit* (ADR for software, character doc for an RPG, shopping list for a remodel). It is emphatically **not** seeds' value proposition.

**Learn from (what still holds).** seeds *is* the IBIS lineage, and two things from that family are genuinely thin in the tool today:
- **Options and arguments as first-class** (IBIS Positions/Arguments, QOC). seeds has idea/question/decision/concern but no explicit "competing option" or "pro/con" structure; `seeds-9/36/44` wrestled with "where do alternatives and rationale live?" and left it open. The landscape's renewed interest in capturing the *why* makes this worth revisiting — but as deliberation structure, not as ADR output.
- **DRed's embedded-in-workflow lesson.** Rationale capture works only when it's *in* the workflow, never a separate step. seeds' whole agent-is-the-interface design is the right instinct; the seeds-112 capture gap is exactly where it's not yet embedded enough.

**On convergence (recalibrated).** My first draft pushed Loomio-style time-boxing to fight "exponential growth" (seeds-45). But Ryan reports **"Focus"** as a *top-four surprise*: discrete seeds + `resolve` + `defer` already make him stop when the seeds he cares about are resolved — *"I've never been so focused in a planning session."* Convergence is largely self-solving via the tool's shape. The real gap isn't *too many* seeds; it's **completeness** (seeds-60) — not knowing which seeds you *failed* to create. Different problem (see the moves below).

### C. Transcript & session capture — *the raw source seeds should consume*

**Learn from.** git-memento binds the *why* to the commit via git notes, with `--summary-skill` to **distill while preserving the full audit** — the exact distill-but-keep pattern seeds wants. This is the **clancey leg** of the capture trio (seeds-156): clancey passively records what already happened; seeds turns selected raw material into deliberation.

**The opportunity (and a real gap).** seeds' hardest named problem, the **capture-in-the-moment gap** (seeds-112), is that agents capture *resolved* deliberation more reliably than *active* deliberation — so the journey is partly reconstructed from memory rather than written live. The answer the field suggests is to let seeds *eat* raw capture: glean seeds from a clancey transcript, a dictated brain-dump, or a meeting (seeds-126 inbox model, seeds-142 dedupe-and-create via the already-built `suggest`). This is complementary, not competitive — and it's the most leverage-rich integration seeds has available.

### D. Agent memory & context engineering — *the architecture challenge, answer it on purpose*

**The live challenge.** Tim Kellogg's *"the only structure LLMs need is tokens… knowledge graphs and SQL-backed models are bad ideas"* is a direct shot at seeds' SQLite-and-relationships core and at `seeds-42` (graph DB — currently **deferred, not rejected**). Notably, **beads itself removed ~27,000 lines** (SQLite backend, daemon/RPC, sync) in its v0.50–v0.56 simplification — independent evidence pointing the same way.

**The honest answer worth writing into a seed.** seeds' structure earns its keep for the *human-and-history* job — lifecycle, blocking, hierarchy, the deliberation graph months later — not as scaffolding the model needs to reason. And the *agent-facing* surface already respects Kellogg: `prime`'s digest is **titles only, bodies on demand** — progressive disclosure, not a memory dump. The genuine refinements: keep the static `prime` preamble (~100 lines of guidance) from bloating, and **give seeds-42 a principled "no"** rather than leaving it deferred — Kellogg + beads' own retreat from graphs both argue against it.

### E. Decision traces, context graphs & GraphRAG — *stay in your lane*

**Already settled.** The three-memory-types frame (episodic/semantic/procedural) clarifies that seeds captures almost purely **episodic** deliberation. ConPort is the nearest enterprise cousin, and the distinction is already a recorded *decision* (seeds-83.4): *"ConPort stores conclusions; seeds tracks the journey… cherry-pick MCP, FTS, typed links while preserving the deliberation-first identity."* FTS is now built; **MCP was deliberately deferred** (seeds-85, in favor of better CLI/prime/skills/hooks). Nothing here changes the verdict: stay episodic, don't chase semantic/procedural memory.

### F. Tacit-knowledge extraction (Meta) — *the mode seeds is missing*

**Learn from.** Meta's pre-compute engine validates seeds' own ideas and adds one it lacks. The **"compass, not encyclopedia"** compact context file (~1,000 tokens) is the right shape for the **knowledge-artifact** concept (seeds-90/91); *"context that decays is worse than no context at all"* says captured intent needs **staleness/re-validation**, which seeds doesn't model; and the 5-standardized-questions template is a reusable gleaning prompt.

**The new mode.** seeds is *capture-at-source* (live deliberation). Meta is *extract-from-residue* (mine the why out of artifacts). A **proactive extraction / gleaning mode** — point seeds at a codebase, a doc set, or a transcript backlog and have it propose seeds — would extend seeds-74.2/125/126 from "sweep this conversation" to "pre-compute over this corpus," and it directly attacks the completeness gap (seeds can't surface what you never considered if it only ever sees what you said out loud).

### G. Intent in the harness / ticket / AGENTS.md — *the honest low-tech rival*

**Reframed as the real competitor.** For most teams, "write the why down" will just mean *a flat `AGENTS.md`/`CLAUDE.md`*. That's the low-tech rival seeds actually competes with — and the honest answer is **not** "make seeds generate AGENTS.md" (that's the ADR trap again). It's that `AGENTS.md` holds the *settled residue* — the conventions that survived — while seeds holds the *live, branching, partly-unresolved deliberation* a flat file structurally cannot: open questions, rejected options with reasons, "waiting on Mark," six children that disagree. The dividing line is the same one seeds draws against ADRs. No new feature needed; just clarity that these are different jobs.

### H. PKM & the backlash — *useful conscience, wrong diagnosis*

files.md's warning — *"the more my system grew, the more I deferred the work of thought"* — is the field's conscience, and seeds shares its healthy instincts (plain JSONL, git, minimal, agent-readable). But the warning is about *accumulation as procrastination*, and Ryan's lived "Focus" surprise suggests seeds doesn't have that disease — it pushes toward resolution, not hoarding. The real limitation in the same neighborhood is the opposite one: **completeness** (seeds-60), the forest that won't tell you which trees you forgot to plant. Keep the minimalist ethos (it's a moat); aim the energy at completeness, not anti-accumulation.

### I. beads + the deliberation-tooling category — *the existential question, asked and answered*

This is the family my first draft mishandled, so it gets the most space.

**beads is the real "could-replace" candidate — and the question is settled.** seeds-12.x asked it directly: beads v0.50–v0.56 grew wisps (ephemeral capture), molecules (templates), `supersedes`/`replies_to`/`duplicates`, threaded messaging, queryable metadata, even a `decision` issue type and a `bd remember` memory store. *"Is seeds a tool or a philosophy?"* The `beads-investigation.md` did the legwork and concluded **no, beads has not absorbed seeds** — on Yegge's own boundary statements: *"Beads is an execution tool,"* *"Beads doesn't have a planning system,"* *"finished issues and future issues don't really belong in Beads."* The adjacent features are execution-supporting metadata: `bd remember` is an operational-insight store ("auth uses JWT"), `bd --type=decision` is an after-the-fact ADR, wisps are agent-ops signals (heartbeat/error/gc). None is structured for *"should we do this at all?"* deliberation. The honest caveat Ryan keeps: *"if a future beads grows a comfortable place for all of that, I'll happily migrate. The investment is in the deliberation surviving"* — seeds is held lightly, on purpose.

**intent.build is the nearest direct competitor** (seeds-74.3, researched): *"the system of record for human decisions in software,"* three surfaces (Capture/Arena/Repo), versions decisions in an `intent/` dir. But it's **code-centric and captures outcomes, not the journey** — auto-recorded decisions, not the branching exploration. seeds' differentiators hold: domain-agnostic, journey-first, and **AI-as-participant**.

**Learn from.** Loomio's time-boxed *discussion → proposal → decision* (workflow design, even if convergence is less urgent than I thought). And **Yorick's** separation of *decision quality* from *outcome luck*: seeds captures the resolution *at close* (built — seeds-134) but never asks, weeks later, *did it pan out?* That **retrospective** loop is the one genuinely new idea here, and a modest one.

**The differentiator to lean on.** seeds-7 and seeds-117 already frame the vision as **AI-as-participant, not AI-as-secretary** — the agent raises its own questions, captures its own reasoning, proposes conclusions, Ryan steers. The `feedback`/"closer" skill is the smallest expression of it (and seeds-151.2 is a sharp lesson: the closer works *user-initiated*, breaks when the agent ritualizes it). This is what separates seeds from passive tools like intent.build *and* from the ambient recording firehose: seeds is where deliberation is *conducted*, not just *recorded*.

---

## The moves, prioritized (revised)

Ranked by leverage, grounded in what's actually built and what Ryan actually names as open:

1. **Close the capture-in-the-moment gap (seeds-112).** The #1 named limitation: agents capture *resolved* deliberation, not *active* deliberation. Ryan is already "letting a couple of seeds germinate" here (hooks, backfill). This is also where seeds meets the landscape's distillation problem — and where consuming raw capture (clancey transcripts, dictation, meetings via the built `suggest`/gleaning) pays off. **Highest leverage.**

2. **Own reasoning-compression / distillation (seeds-116/120).** seeds' own framing — *"the gap between full conversation transcripts (too verbose) and compressed summaries (too lossy)"* — is, almost verbatim, the single biggest *unsolved* problem in the entire landscape. Nobody has cracked it. seeds is already pointed at it. Make it the headline bet, with the knowledge-artifact (seeds-90/91) as a compact, staleness-aware "compass" file à la Meta.

3. **Attack the completeness gap (seeds-60), agent-mediated.** *"Doesn't tell you what you HAVEN'T explored."* This — not convergence — is the real limitation, and the fix must reach Ryan *through the agent* (he never touches the CLI): the agent surfacing "three of twenty source columns still have no seed," not a human dashboard. Proactive gleaning/extraction (family F) is one route in.

4. **Hold the boundaries — a discipline, not a feature.** Don't become a planning/spec tool (family A); don't slide toward ADR-style conclusion-output (family B/G). The niche is protected by *what seeds refuses to do*. This replaces my first draft's top two recommendations, which pushed seeds toward exactly those drifts.

5. **Settle structure-vs-tokens (Kellogg + beads' own simplification).** Give seeds-42 (graph DB) a principled "no"; keep the structure that serves humans-and-history, keep `prime` a small curated block. Write the rationale down as a decision so it stops being deferred.

6. **Lean into AI-as-participant (seeds-7/117, the `feedback` skill).** The differentiator versus passive intent.build and versus the recording firehose alike — seeds is where deliberation is *conducted*. Keep skills prompt-macro-scale (seeds-152.2); the closer-pattern lesson (seeds-151.2) shows how much a single line can carry.

*Dropped or demoted from the first draft:* "make ADRs/AGENTS.md the fruit" (contradicts the founding pivot); "add convergence pressure / time-boxing" (Focus already delivers it); "outcome-tracking" survives only as the modest *retrospective* Yorick idea, since resolution-at-close is already built.

## What's already built vs. deliberated vs. genuinely new

**Built** (stop recommending these): the deliberation lifecycle, first-class questions + blocking, the `resolution` field (seeds-134), FTS5 `search` + `suggest` dedup, `recent`, `doctor`, body-ref validation, JSONL export, read-only web UI, `prime` + metadata-only digest (progressive disclosure), prompt-macro skills (`feedback`, `seeds-to-beads`).

**Deliberated / open** (the landscape mostly *validates* these): graph DB (seeds-42, deferred), spec-graduation (seeds-118/122 — and the landscape argues *against* pursuing it), knowledge artifacts (seeds-90/91), reasoning compression (seeds-116/120), multi-perspective deliberation (seeds-117), MCP (seeds-85, deferred), gleaning/sweep (seeds-74.2/125/126/142), completeness (seeds-60), capture-in-the-moment (seeds-112), the ConPort distinction (seeds-83.4), the beads boundary (seeds-12.x, resolved).

**Genuinely new from the landscape** (worth fresh seeds): the **Triple Debt vocabulary** as crisp external positioning (intent debt = seeds' reason to exist, now with a peer-reviewed name); **git-memento's distill-but-keep** binding pattern for capture-consumption; **Kellogg's structure-vs-tokens** challenge as the decision that resolves seeds-42; **Meta's after-the-fact extraction** as a new gleaning mode; **IBIS options/arguments** as the under-built deliberation structure (seeds-9/36/44); and **Yorick's retrospective outcome** loop.

## The closing thought

seeds doesn't need to chase this landscape — it got there first, and it already knows what it is. The published three-layer model and the beads boundary are settled; the founding pivot away from ADRs is the discipline that keeps the niche clean. The work that's left is narrow and hard, and it's the *same* work the whole field is stuck on: capture the deliberation while it's still happening, and distil it into something durable without flattening it into a conclusion. seeds has those exact problems written down as its own next seeds. That's not a tool playing catch-up — it's a tool standing where the field is only now realizing it needs to be.
