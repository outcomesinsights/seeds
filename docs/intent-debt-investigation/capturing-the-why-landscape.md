# Capturing the Why — A Landscape of Intent, Deliberation, and Memory in the AI Era

> **What this is.** A field guide to a problem space that a lot of smart people started naming, loudly, in early-to-mid 2026: AI makes *artifacts* (code, transcripts, summaries, notes) almost free, while leaving *intent* — the rationale, the deliberation, the "why" behind the artifact — as scarce and uncaptured as ever. This document maps the diagnosis, the deeper roots, and the whole sprawling solution space of tools and approaches racing to fill the gap. It is written as an opinionated tour, not a literature review. seeds lives only in the appendix; the body is about the territory.
>
> Compiled 2026-06-11 from ~40 sources — most read first-hand, some synthesized from web research, and the deliberation-tooling lineage building on seeds' own `deliberation-tools-research.md`.

---

## The one idea that ties it all together

Two forces are colliding, and almost every article in this space is standing at the intersection pointing at one or the other.

**Force one: artifacts got cheap, so intent became the scarce thing.** When a model can write the code, refactor the mess, and even reconstruct a lost mental model on demand, the one input it *cannot* manufacture is the human reason a thing exists. Addy Osmani says it cleanly: *"An agent can't generate intent, because intent is the one input that has to come from you."* The value moved. Code is now the cheap, regenerable output; the durable, expensive, human-only input is the *why*.

**Force two: capture got frictionless, so we're drowning in artifacts that aren't intent.** Simultaneously — and this is the cruel part — AI made *recording* nearly free. Every meeting is transcribed, every agent session is logged, every call has an AI notetaker. We have more captured material than ever in history, and almost none of it is distilled intent. A meeting yields an audio file, a machine transcript, an AI summary, and maybe formal minutes — four artifacts, no hierarchy, and the actual decision buried somewhere inside. As one practitioner puts it, *"a raw transcript is a starting point, not a solution."*

Put them together and you get the white space the entire ecosystem is rushing into:

> **Capture ≠ comprehension ≠ intent.** Recording is the cheapest, shallowest layer. Intent is the most expensive, scarcest layer. Producing more of the former does not yield the latter — and, as we'll see, can actively degrade it.

Hold that spectrum in your head — *raw recording → transcript → summary → structured memory → decision trace → spec/rationale → genuine deliberation* — because every tool in Part II is really just a bet on which slice of it to occupy.

---

# Part I — The Diagnosis

## 1. The Triple Debt Model — the keystone

If you read one thing in this space, it's Margaret-Anne Storey's **["From Technical Debt to Cognitive and Intent Debt: Rethinking Software Health in the Age of AI"](https://queue.acm.org/detail.cfm?id=3807966)** (ACM Queue; [arXiv 2603.22106](https://arxiv.org/abs/2603.22106)). It's the paper that gives the whole conversation its vocabulary, and it came out of Martin Fowler's Thoughtworks "Future of Software Development" retreat in February 2026. Two widely-circulated blog posts are downstream of it — Storey's own ["What I'm Hearing About Cognitive Debt"](https://margaretstorey.com/blog/2026/02/18/cognitive-debt-revisited/) and Osmani's ["The Intent Debt"](https://addyosmani.com/blog/intent-debt/) — and Thoughtworks built its [Technology Radar v34](https://www.thoughtworks.com/about-us/news/2026/combat-ai-cognitive-debt-radar-v34) theme around it.

The model is three kinds of debt, distinguished by **where each one lives**:

| Debt | Lives in | Is the erosion of… |
|------|----------|--------------------|
| **Technical debt** | the code | changeability |
| **Cognitive debt** | people | shared understanding ("the team lost the plot") |
| **Intent debt** | artifacts | externalized rationale, goals, constraints — the *why* |

From the abstract, verbatim: intent debt is *"the absence of externalized rationale that developers and AI agents need to work safely with code."* The crucial word is **externalized** — intent that lives only in your skull isn't an asset anyone (human or agent) can use.

Why does AI flip the priorities? Because it attacks the first two debts and leaves the third exposed. Agents are good at refactoring technical debt and can rebuild lost comprehension on demand — but they have no way to manufacture the original intent. Worse, they paper over the gap: a model *"will invent a confident-sounding reason, which is worse than admitting it doesn't know."* Osmani's per-session framing is the line that stuck with everyone:

> *"Bringing agents onto a team doubles its size overnight with junior people who have no long-term memory."*

A team running 20 parallel agents is 20 teammates who never met you, can't read your mind, and fill every gap in your intent with a plausible guess — *every session*. Un-externalized intent used to bill you rarely (at onboarding or when the veteran quit). Now it bills you continuously, multiplied per agent.

Two intellectual roots matter here, because they recur across the whole field:

- **Naur's "Programming as Theory Building" (1985).** A program is not its source code; it's a *theory* living in the developers' minds about what it does and how it may change. Fowler's framing of the AI problem is precisely that the code can be pristine and the team can still *"have lost the plot."* The intent axis of his classic 2009 technical-debt quadrant *breaks down* — because, as the cognitive-debt commentary puts it, *"AI does not have intent. It does not deliberate."*
- **McLuhan's "retrieval."** New media revive what old media made obsolete. The paper's sharpest move is to argue that GenAI is *retrieving* a set of practices — specs, tests, ADRs, design rationale — that we let atrophy because, pre-AI, source code itself (good names, clear structure) carried enough intent to get by. When the code is machine-generated, that implicit channel is gone and intent has to be put back, on purpose.

The paper's own list of **"intent artifacts"** — the externalized memory of what a system is for — is essentially the table of contents for Part II of this document: requirements, architectural decision records, implementation plans, tests, specifications, agent instructions/playbooks, and — tellingly — *"AI-assisted intent capture from meetings and conversations."* That last one is the bridge straight into the recording firehose.

## 2. The Recording Firehose — everything is captured, nothing is distilled

The counterpart diagnosis comes from the opposite direction. a16z's **["Everything Is Recorded Now"](https://www.a16z.news/p/everything-is-recorded-now)** (David Haber) argues that workplace recording flipped from opt-in to assumed almost overnight, and that the prize is a "living context layer" — onboard your AI like an employee, let it attend every meeting and *"reason over every interaction and never get bored,"* turning voice into something *"structured, searchable, and queryable."* "Verbal cultures" (it names OpenAI, Shopify) supposedly gain a compounding edge over "written cultures."

It's an investor's bull case, and it's useful precisely because the **best critique sits in its own comment section.** A reader's objection nails the seeds-shaped point:

> *"Once people assume every meeting is recorded… the messy, half-formed thinking that actually produces good decisions tends to migrate to the hallway and the DM. You capture more context, but a thinner, more performed version of it."*

That's the **candor paradox**, and it's the single most important idea in the firehose half of the space: comprehensive capture changes the thing being captured. The more you record, the more the real deliberation flees to where the recorder isn't.

The governance and practitioner literature has converged on the same insight from a risk angle:

- **White & Case, ["When every word is recorded"](https://www.whitecase.com/insight-alert/when-every-word-recorded-ai-meeting-tools-and-new-governance-risks)** — verbatim records can *"inhibit open discussion in boardrooms,"* and the recommended fix is to deliberately *carve out* unrecorded, manual-minutes-only spaces. In other words: institutionalize the hallway.
- **Fortune, ["The dark side of AI meeting notes"](https://fortune.com/2026/02/09/ai-notetakers-are-creating-hr-nightmares/)** — organizations now juggle *"a complex ecosystem of recordings, machine transcripts, AI summaries, decks and conventional minutes,"* each differing in language, attribution, and tone, with no hierarchy and no review. The volume is the problem.
- **Read.ai, ["How AI Transcription Reduces Meeting Overhead"](https://www.read.ai/articles/how-ai-transcription-reduces-meeting-overhead)** — even the vendors concede the point: *"a raw transcript is a starting point, not a solution… The real value shows up when each meeting becomes part of a connected knowledge system."* The framing that recurs everywhere: this is *"a knowledge problem, not a meeting problem."*

And the hardware is racing to record *more*, not less. The consumer "ambient capture" land grab is real — Meta acquired Limitless (the always-on pendant), Amazon acquired Bee (ambient-listening wearable), OpenAI is rumored to be building a context-aware device — explicitly to capture the hallway conversations that escape the Zoom bot. The capture frontier keeps advancing; the candid deliberation keeps fleeing one step ahead of it. The equilibrium nobody wants: record everything, understand less.

## 3. The deeper loss — tacit knowledge and the death of osmosis

Underneath both diagnoses is an older anxiety that AI made acute: the informal, person-to-person channels that used to move intent around are disappearing, and agents never had access to them in the first place.

Dheer's **["Your ticket is a prompt"](https://dheer.co/tickets-are-prompts/)** has the line that crystallizes it: *"Agents don't have hallways."* His argument is that the long-standing "fragmentation disease" — chopping work into ever-smaller atomic tickets — was always broken, but humans hid the breakage by *"catching context in hallway conversations and filling gaps from tribal knowledge."* An agent reads only the ticket text, faithfully reproduces the fragmentation, and three iterations later *"the original outcome was buried under atomic fixes that collectively solved nothing."* His fix — outcome-shaped tickets that preserve the *why* and let the agent derive subtasks — is itself an intent-capture argument.

The same theme runs through Sunil Pai's piece on developer relations "after the cheat-code machine" (the loss of *osmosis* and apprenticeship), and the broader worry that remote work plus agent-generated code has severed the ambient channel through which juniors used to absorb tacit knowledge. Storey's cognitive debt is the team-level name for the same wound: knowledge *"distributed across people, docs, tests, conversations, tooling — not code alone,"* eroding faster than it can be rebuilt.

The throughline of Part I: **the implicit carriers of intent (readable code, hallway talk, the veteran who remembers 2023) are all weakening at once, and the explicit carriers haven't been rebuilt yet.** That's the vacuum.

---

# Part II — The Solution Space

Everyone agrees on the disease. The disagreement — and it's a genuinely interesting one — is about the cure. Here are the families, each with what it is, who's building it, the mechanism, the win, and the catch. I've ordered them roughly from "encode intent before the work" to "reconstruct intent after the work."

## A. Spec-driven development — encode intent *before* execution

The most energetic corner of the field. The thesis: agents fail not by breaking the build but by producing *"the wrong kind of correct"* (disabling a test, cloning the nearest pattern), and the root cause is **underconstrained execution**. The cure is to write durable intent down *first*. Matt Rickard's **["The Spec Layer"](https://blog.matt-rickard.com/p/the-spec-layer)** is the best single read: *"When a decision isn't written down, the agent has to decide it again."*

The striking thing is how many tools are independently rebuilding the same skeleton — **durable context, feature intent, a technical plan, explicit tasks, and verification**:

| Tool | Angle |
|------|-------|
| **GitHub Spec Kit / Kiro** | specs kept next to the change workflow |
| **OpenSpec** | spec as a decision record that survives the change |
| **Tessl** | the spec becomes the thing you edit, not the code |
| **Intent (Augment)** | spec as shared state |
| **Symphony (OpenAI)** | spec as orchestration contract for autonomous runs |
| **CodeSpeak** | machine-readable specs LLMs compile to code; claims 5.9–9.9× compression vs source, plus an explicit *"intent recovery"* tool that extracts requirements from prior agent sessions |
| **Ossature**, **acai.sh** | spec/acceptance-criteria toolkits pitched as the antidote to "slop" |

Rickard's criteria for a *good* spec are worth memorizing: **declarative** (match code to intent, don't replay a brittle patch), **layered** (product requirements don't silently become architecture), and **cheap to revise** (*"if a spec is expensive to update, the process hardens into ceremony and the ceremony becomes the work"*). And his discipline: push mechanical rules *out* of prose into lint/schemas/tests/harnesses — *"smaller specs, harder checks, less guessing."*

A close cousin is **"review the intent, not the code."** Ankit Jain's ["How to Kill the Code Review"](https://www.latent.space/p/reviews-dead) argues that since AI generates code past human review capacity, the approval gate should move upstream to specs and acceptance criteria — humans approve the *intent* before coding, and code becomes a verifiable artifact of the spec rather than the object of judgment.

**The catch — and it's the central live debate in the whole field.** Two objections:
1. **Dijkstra's ghost:** *"a sufficiently detailed spec is code."* Precision doesn't vanish by moving from one notation to another; push abstraction too far and you've reinvented model-driven development's failures.
2. **Intent isn't knowable upfront.** This is the strongest counterweight, and it comes from Thorsten Ball's ["Building Software Is Learning"](https://registerspill.thorstenball.com/p/building-software-is-learning) (pure Naur): *"building new software is learning."* You can't fully specify what you want because the specification *emerges during building*. Full upfront specification is impossible because complete specification *is* the programming. His prescription is the opposite of spec-first: minimize the latency between trying something and hitting reality (hour-long prototypes, README-driven design, tiny merges). 

So the unresolved question the field is arguing about: **is intent something you write down and then execute, or something you discover by executing and must capture as you go?** Both camps are right about different work, and nobody has reconciled them.

## B. Decision records & design rationale — the pre-AI tradition, newly urgent

This is the McLuhan "retrieval" in action: the AI era is rediscovering a 40-year-old discipline. The lineage seeds itself descends from:

- **ADRs (Architecture Decision Records)** and **RFCs** — lightweight, in-repo, "why we decided X at the moment we decided it." Osmani explicitly prescribes both, plus *"AGENTS.md as an intent ledger,"* as the antidote to intent debt.
- **IBIS → gIBIS → QuestMap → Compendium** — the design-rationale family (Issues → Positions → Arguments). Compendium remains the most complete implementation, if unmaintained.
- **Argdown** — markdown-flavored argument mapping, git-friendly, with VS Code/Obsidian plugins.
- **Kialo / ConsiderIt / Loomio** — structured argumentation and group deliberation; Loomio's *discussion → proposal → decision* with **time-bounded proposals** is a particularly good model for preventing endless deliberation.
- **DRed (Rolls-Royce)** — the one design-rationale tool that achieved real industrial scale, and the reason why matters: **it was embedded in the workflow, not bolted on as a separate step.** This is the single most important lesson in the whole category. Rationale capture that asks people to stop and document separately fails; rationale capture that *is* the workflow succeeds.

The catch with this whole family: historically, **adoption is terrible** unless capture is frictionless and embedded. People won't context-switch to a separate "now write the rationale" step. Every modern entrant is really trying to solve that adoption problem with automation or by riding inside an existing workflow.

## C. Transcript & session capture for code — bind the conversation to the artifact

The most direct response to "the why is lost when only the code is committed." Keep the AI session and attach it to the work.

- **[git-memento](https://github.com/mandel-macaque/memento)** — the cleanest implementation. It attaches AI session transcripts to commits as **git notes**: `git memento commit <session-id>`, then `push`/`notes-sync` so teammates get them. The design virtue is that it leverages a native Git feature, so the *why* (prompts, constraints, rejected alternatives) travels with the *what* through rebases, and a `--summary-skill` can condense the transcript while preserving the full audit in a separate ref.
- **AgentLogs / claude-code-viewer** (from Philipp Spiess' ["Software Collaboration in the AI Age"](https://spiess.dev/blog/software-collaboration-in-the-ai-age)) — same diagnosis ("agent transcripts are lost to Git commits"), built as a store with secret-scanning because transcripts are *"high-risk artifacts that must not leak credentials."*
- **Intercom's instrumentation** (Brian Scanlan) — the heavyweight version: every Claude Code action to OpenTelemetry, session transcripts to S3, post-session Haiku analysis that auto-classifies gaps and files issues.

The win: intent stays adjacent to the result. The catch: a transcript *is* the firehose — raw, verbose, mostly noise — unless it's distilled. The `--summary-skill` is an admission that the raw artifact isn't the deliverable. Which is the recurring problem: **binding the transcript is easy; distilling it into durable intent is the unsolved part.**

## D. Agent memory & context engineering — give the agent durable recall

A fast-moving sub-field about how agents remember across sessions. Tim Kellogg's **["Agent Memory Patterns"](https://timkellogg.me/blog/2026/04/27/memory-patterns)** is the best map. His taxonomy is deliberately un-academic — **files** (data/knowledge), **memory blocks** (*"a learnable system prompt,"* injected inline for guaranteed visibility), and **skills** (indexed, progressively disclosed) — each supporting explore/read/write. The patterns that matter for *intent*: an **experience cache** / editable skills (the agent records *why something mattered* — "weird, interesting, annoying" — not just facts) and an **append-only event log** for grounded recall.

His most provocative claim, and a direct shot across the bow of family E below: *"The only structure LLMs need is tokens. They reason just fine in token space."* He explicitly flags **knowledge graphs and SQL-backed models as bad ideas** — impose rigid schema and you fight the model's native fluency. The failure mode he names: memory blocks that grow too big *"tend to confuse the agent."*

Surrounding this: the **"context engineering"** discourse generally, **context rot** in long-running agents (Osmani's ["Long-running Agents"](https://addyosmani.com/blog/long-running-agents/)), context-pruning techniques, and the "filesystems are having a moment" observation that the filesystem is becoming the agent's memory substrate. The distinction that matters across all of it: memory of *facts* is not memory of *why-it-mattered*, and most systems are much better at the former.

## E. Decision traces, context graphs & enterprise knowledge — the org-scale version

Where family D is one agent's memory, this is the institution's. The anchor is the InfoWorld / Memgraph piece **["Are decision traces enough?"](https://www.infoworld.com/article/4156909/contexts-graphs-ai-memory-and-enterprise-knowledge-are-decision-traces-enough.html)**, responding to Foundation Capital's "context graph" concept.

A **decision trace** is episodic memory of *how a decision was actually made* — *"how rules were applied, where exceptions were granted, how conflicts were resolved, who approved what."* The article's key argument is that traces alone aren't enough; serious enterprise AI needs **three memory types** (a useful frame that recurs):

- **Episodic** — how decisions were made (decision traces)
- **Semantic** — the organization's private facts the model was never trained on
- **Procedural** — how work is actually done

*"Skip one, and you effectively give AI the freedom to hallucinate in that domain."* The proposed substrate is a **"graph of graphs"** — a context graph as operational memory sitting *above* existing systems (ERP/CRM/warehouse), routing queries — and **GraphRAG**, on the argument that enterprise questions are relationship-shaped and *"vector search finds similar text but doesn't capture the structure of relationships."*

Note the **direct philosophical clash with family D**: Kellogg says graphs are a bad idea and tokens are enough; the context-graph camp says structure is the only thing that scales relational truth. This is an unsettled and important fault line — structure vs. natural language as the right substrate for captured intent.

## F. Tacit-knowledge extraction — reconstruct intent *after* the fact

The inverse strategy: instead of capturing intent at the source, mine it back out of the codebase. **Meta's** ["How Meta Used AI to Map Tribal Knowledge"](https://engineering.fb.com/2026/04/06/developer-tools/how-meta-used-ai-to-map-tribal-knowledge-in-large-scale-data-pipelines/) is the standout. A "pre-compute engine" of 50+ specialized agents (explorers, analysts, writers, critics, fixers) read every file in a 4,100-file pipeline once and answered five standardized questions per module — including, explicitly, *"What tribal knowledge is buried in code comments?"* — surfacing 50+ undocumented patterns (silent field-rename conventions, append-only enum constraints) and packaging them as 59 compact *"compass, not encyclopedia"* context files (~1,000 tokens each).

Two lines worth keeping:
> *"Context that decays is worse than no context at all."* (so the system self-maintains and re-validates)
> *"Without context, agents burn 15–25 tool calls exploring… and produce subtly incorrect code."*

The win: tacit intent *can* be systematically externalized at scale. The catch: it reconstructs *what the code implies*, not *why the humans chose it* — it recovers convention and constraint, but a genuinely arbitrary-or-deliberate decision ("was 300ms a UX call or a number someone typed once?") is gone if it was never recorded. Extraction complements source-capture; it doesn't replace it.

## G. Intent in the harness, the ticket, and the instructions

A quieter family: the durable-instruction surfaces that encode standing intent for agents. **AGENTS.md / CLAUDE.md** as an "intent ledger" (Osmani) — what the team *means*, not just config. The ticket as the unit of intent (Dheer, family A's cousin). And the observation that *"today's harness is tomorrow's prompt"* — the scaffolding you build around the agent is itself accumulated, externalized intent. Small surface, but it's where a lot of real intent actually lands in practice today.

## H. PKM, second brains — and the backlash that matters

The personal-knowledge-management tradition (Obsidian, Logseq, Roam, Tana, Capacities, Mem; the spatial branch — Heptabase, Kinopio, Muse) is the consumer ancestor of all this: networked thought, block-level capture, bidirectional links. Logseq's TODO/LATER states are the closest off-the-shelf analog to a deliberation lifecycle; Kinopio's "patch cables" model idea relationships well.

But the most *useful* thing in this family right now is the **backlash**, because it's the field's conscience. **[files.md](https://github.com/zakirullin/files.md)** (and the Joan Westenberg essay it quotes, "I Deleted My Second Brain") makes the argument the whole space needs to hear:

> *"The more my system grew, the more I deferred the work of thought to some future self."*
> *"Reading without action is entertainment. A form of procrastination."*

The "first brain vs. second brain" critique: elaborate capture systems create an *illusion of mastery* while postponing the real cognitive work indefinitely. This is the essential caution for everything in Part II — **tooling-up capture can become a sophisticated way to avoid thinking.** Any intent-capture tool has to earn its friction or it becomes dopamine-flavored procrastination.

## I. Deliberation & decision-support tooling — the dedicated category

Finally, the tools built specifically to capture *deliberation* (not tasks, not code, not notes) — the closest cousins to anything in this space and the category seeds' own research already mapped:

- **intent.build** — auto-captures decisions from AI coding sessions (Claude Code, Cursor, Codex, Gemini), maps provenance between code and conversation, CRDT version history, "mindful making." Verdict from the prior research: solves *"don't lose decisions"* but not *"help me deliberate"* — it captures outcomes, not the journey.
- **Loomio** — group deliberation as discussion → proposal → time-bounded decision, with a searchable archive. Best workflow model in the bunch.
- **Decision journals** (Decision Journal App, Yorick, Loqbooq) — track a decision and its later outcome; Yorick smartly separates decision *quality* from outcome *luck*.
- **SequentialThinking MCP** — documents an agent's reasoning steps, with revision, inside a conversation.
- **Academic**: the Human-AI Deliberation framework (CHI 2025) and the **Habermas Machine** (Science, 2025), which outperformed human mediators at helping groups find common ground — early evidence that AI-*mediated* deliberation, not just AI-captured deliberation, is viable.

The category's defining gap (per the prior survey): nobody treats **the deliberation process itself as the first-class artifact**, journey and all, in a CLI/agent-native form. Most tools capture the *destination*; this corner is about capturing the *road*.

---

# Part III — Cross-cutting themes and the tensions worth watching

Step back and the same fault lines run through every family. These are the things to actually argue about.

1. **The capture↔intent spectrum is the master lens.** Raw recording → transcript → summary → structured memory → decision trace → spec/rationale → live deliberation. Everything in Part II is a bet on a slice. Cost and value both rise as you move right. The firehose tools live on the cheap-left; ADRs and specs live on the expensive-right; the genuinely hard, mostly-unbuilt thing is the *machinery that moves material rightward* — distillation.

2. **Distillation is the field's great unsolved problem.** Universal agreement that raw capture ≠ useful intent. Near-universal hand-waving about how you compress a sprawling deliberation into durable rationale *without losing the journey that justifies it*. git-memento bolts on a `--summary-skill`; Read.ai gestures at "a connected knowledge system"; Meta re-validates to fight decay. Nobody has nailed it. Whoever does owns the category.

3. **Upfront intent vs. emergent intent.** Spec-driven development (write it, then build) vs. Naur/Ball (build to discover, then capture). This isn't resolvable in the abstract — it's a function of how novel the work is. The interesting tools will let intent be *both* prescribed and harvested.

4. **Capture-at-source vs. reconstruct-after.** a16z and git-memento capture as it happens; Meta reconstructs from the residue. Source-capture gets the genuine *why* but suffers the candor paradox and the friction problem. Reconstruction scales and needs no discipline but only recovers what the artifact implies. They're complements, and a serious system probably needs both.

5. **The candor paradox / observer effect.** The deepest and least-appreciated tension: *comprehensive capture degrades what's captured.* Record everything and the real thinking flees to the unrecorded margins. This is why "just record it all" (the a16z bull case) is self-undermining, and why *intentional, opt-in, low-stakes* capture surfaces may beat *ambient, total* ones. The governance answer — deliberately protect unrecorded space — is an admission that more capture is not strictly better.

6. **Embedded-in-workflow vs. separate step.** DRed's hard-won lesson, validated by every failed rationale tool: capture that asks you to stop and switch contexts dies; capture that *is* the workflow survives. The friction budget is brutal.

7. **Structure vs. natural language.** Kellogg ("tokens are all the structure you need," graphs are a trap) vs. the context-graph/GraphRAG camp ("relationships need graphs"). A real, unsettled architectural fork for how captured intent should be stored.

8. **Who is the audience now?** Historically intent-capture served future-humans (the next maintainer). Increasingly the primary reader is an *agent* — and agents have different needs (machine-readable, retrievable, compact, "compass not encyclopedia"). This is quietly reshaping the *form* intent should take.

9. **Capture as avoidance.** files.md's warning, applicable to the whole field: an elaborate capture habit can be procrastination wearing a productivity costume. The test for any tool here is whether it makes thinking *happen*, or just makes *not-thinking* feel organized.

10. **The McLuhan retrieval is real.** This isn't a new problem with new answers; it's an old discipline (RFCs, ADRs, IBIS, literate programming, design rationale) made suddenly load-bearing because the implicit channels that let us skip it have gone dark. The winners will likely be old ideas in agent-native clothing.

---

# Appendix — Where seeds sits

*(Per the brief, kept short. The body above is the deliverable; this is orientation.)*

**Placement.** seeds lives in family **B/I** — the design-rationale and dedicated-deliberation lineage (IBIS → Argdown → Loomio), rendered CLI-first and agent-native. Its distinctive bet, which no surveyed tool makes, is to treat **the deliberation process itself as the first-class artifact** — the journey, not just the resolved decision — inside the "capture trio" the project already articulates (seeds-156): **beads** for tasks, **clancey** for passive decision/memory capture, **seeds** for active deliberation. On the spectrum in Part III, seeds deliberately occupies the expensive-right end (structured deliberation), which is exactly the territory the whole field agrees is valuable and underserved.

**What the landscape validates.** The premise is no longer idiosyncratic — Storey's Triple Debt gives it a peer-reviewed name (*intent debt* = seeds' whole reason to exist), and the candor paradox is a positive argument *for* an intentional, opt-in deliberation surface as the antidote to ambient recording. seeds' own published positioning already maps the territory as three layers — *planning* tools (OpenSpec, Spec Kit) / *execution* (beads) / *deliberation* (seeds) — and pointedly **rejects ADRs** as the answer (an ADR records the conclusion, not the journey, which is the whole thing seeds set out to keep). So where the landscape's spec-driven-development wave (Rickard's "The Spec Layer," Spec Kit, Kiro, OpenSpec, CodeSpeak) can look like "a missing layer between seed and bead," seeds has already decided *not* to be that layer — it feeds planning and execution rather than becoming either. The convergence is real; the response is a boundary, not a feature.

**Already on the radar** (so the landscape isn't telling you anything new here): ConPort (seeds-83), intent.build (seeds-74.3/80/81), context graphs / graph DB (seeds-42), reasoning compression (seeds-116/120), multi-perspective deliberation (seeds-117), knowledge artifacts (seeds-90/91), source-document gleaning (seeds-125/126).

**Newer entrants worth a look:**
- **The Triple Debt vocabulary itself** — the cleanest problem statement and positioning seeds could adopt; "intent debt" is a better elevator pitch than anything currently in the README.
- **git-memento's binding model** — transcript-to-artifact via git notes; a concrete pattern for seeds' seeds-74 (link seeds to source conversations) and seeds-115 (link seeds to experiments).
- **Tim Kellogg's anti-schema stance** — a direct, credible challenge to seeds' SQLite/typed-relationship structure (and to seeds-42's graph-DB question); worth pressure-testing whether seeds' structure helps the agent or fights it.
- **Meta's after-the-fact extraction** — a model seeds doesn't have: *reconstruct* deliberation from existing artifacts, not just capture it live. Complements the gleaning idea.
- **DRed's embedded-in-workflow lesson + the candor paradox** — together the strongest design constraint: seeds wins only if capture is so low-friction it disappears into the work, and only if it's the *safe, intentional* place thinking goes *because* everything else is being recorded.

**The one-line takeaway.** The whole field now agrees on seeds' premise — intent and deliberation are the scarce, uncaptured thing — and the field's single biggest *unsolved* problem (distilling raw deliberation into durable intent without losing the journey) is precisely the bet seeds is placed on. That's a good place to be standing. For the full seeds-specific treatment — grounded in the codebase, the live deliberation log, and the published positioning — see the companion [`capturing-the-why-seeds-evaluation.md`](capturing-the-why-seeds-evaluation.md).

---

## Sources

**In the diagnosis (Part I)**
- Storey — Triple Debt paper: [ACM Queue](https://queue.acm.org/detail.cfm?id=3807966) · [arXiv](https://arxiv.org/abs/2603.22106) · [getDX writeup](https://getdx.com/blog/cognitive-debt-the-hidden-risk-in-ai-driven-software-development/) · [Thoughtworks Radar v34](https://www.thoughtworks.com/about-us/news/2026/combat-ai-cognitive-debt-radar-v34) · [RDEL #137](https://rdel.substack.com/p/rdel-137-what-kinds-of-new-debt-are)
- Storey — [What I'm Hearing About Cognitive Debt](https://margaretstorey.com/blog/2026/02/18/cognitive-debt-revisited/) · [original](https://margaretstorey.com/blog/2026/02/09/cognitive-debt/)
- Osmani — [The Intent Debt](https://addyosmani.com/blog/intent-debt/)
- a16z — [Everything Is Recorded Now](https://www.a16z.news/p/everything-is-recorded-now)
- [White & Case — When every word is recorded](https://www.whitecase.com/insight-alert/when-every-word-recorded-ai-meeting-tools-and-new-governance-risks) · [Fortune — dark side of AI meeting notes](https://fortune.com/2026/02/09/ai-notetakers-are-creating-hr-nightmares/) · [Read.ai — transcription overhead](https://www.read.ai/articles/how-ai-transcription-reduces-meeting-overhead)
- [Dheer — Your ticket is a prompt](https://dheer.co/tickets-are-prompts/) · Sunil Pai — [developer relations after the cheat code machine](https://sunilpai.dev/posts/developer-relations/)

**In the solution space (Part II)**
- Specs: [Rickard — The Spec Layer](https://blog.matt-rickard.com/p/the-spec-layer) · [CodeSpeak](https://codespeak.dev/) · [Latent.Space — How to Kill the Code Review](https://www.latent.space/p/reviews-dead) · [Ball — Building Software Is Learning](https://registerspill.thorstenball.com/p/building-software-is-learning)
- Transcripts: [git-memento](https://github.com/mandel-macaque/memento) · [Spiess — Software Collaboration in the AI Age](https://spiess.dev/blog/software-collaboration-in-the-ai-age)
- Memory/graphs: [Kellogg — Agent Memory Patterns](https://timkellogg.me/blog/2026/04/27/memory-patterns) · [InfoWorld — Are decision traces enough?](https://www.infoworld.com/article/4156909/contexts-graphs-ai-memory-and-enterprise-knowledge-are-decision-traces-enough.html) · [Osmani — Long-running Agents](https://addyosmani.com/blog/long-running-agents/)
- Extraction: [Meta — Mapping Tribal Knowledge](https://engineering.fb.com/2026/04/06/developer-tools/how-meta-used-ai-to-map-tribal-knowledge-in-large-scale-data-pipelines/)
- PKM/backlash: [files.md](https://github.com/zakirullin/files.md)
- Deliberation tooling: building on seeds' own `deliberation-tools-research.md` (Argdown, Compendium, Loomio, ConsiderIt, intent.build, decision journals, Habermas Machine, et al.)

**Internal cross-references (seeds repo, not in oimnibus):** `docs/deliberation-tools-research.md`, `docs/seed-vs-spec-tension-2026-05-19.md`, `docs/intent-build-overview.md`, `docs/what_i_know_about_{adr,rfc,deliberation_and_decision_making}.md`.
