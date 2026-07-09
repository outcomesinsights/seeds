# Blog Outline — "Upstream of Intent" *(working title)*

> **What this is.** A skeleton for the follow-up blog post positioning seeds within the early-2026 "capturing the why" / intent-debt conversation. Assembled 2026-06-15 from the intent-debt investigation docs in this directory, Ryan's dictated [`feedback.md`](feedback.md), and the seeds filed during that review (seeds-158 through seeds-174).
>
> **This is an outline, not a draft.** The beats below are arguments and the source material to deploy — the prose is Ryan's to write. Where a beat quotes Ryan, it's pulled from his own dictated words so it's reusable verbatim.
>
> **Spine (seed-168):** *seeds is upstream of intent.* The field named a real scarcity but picked the wrong unit — intent is the settled residue; seeds keeps the **journey** that produces it. And the one thing the argument used to hang on — does any of this reach the agent? — has now been investigated (seed-169).

---

## Working titles

- **Upstream of Intent**
- Intent Is the Wrong Unit
- I Commit Code I've Never Read. I Still Won't Let It Decide What to Build.
- The Journey, Not the Destination

---

## Framing calls already made (so they don't get re-litigated mid-draft)

- **Decline the "intent debt" vocabulary as the banner (seed-167).** Engage the conversation, push off its terms. "Intent is the wrong unit" — it names the destination; seeds is the journey to it.
- **Don't strawman the field's audience.** Intent-capture is pitched for **both** humans *and* agents (Storey's definition says so explicitly), but the field is trending hard toward the *agent* as the primary reader. The honest move is: "the field is excited about the agent-as-audience shift — so I checked whether that's how my own pipeline works." (→ §4)
- **AGENTS.md is *not* a real rival** — cut it. It's a standing-instructions file loaded every session; deliberation is branching, voluminous, mostly-resolved. Pour the journey into it and you blow context and blend settled convention with open exploration. If used at all, flip it into a *positive*: that's exactly why deliberation needs a retrieved-on-demand store (`prime` digest + `show`), not a flat file.
- **The investigation is resolved (seed-169), so §4 is the climax, not an open question.** Intent reaches the implementer *distilled into the bead*, not by the agent reading seeds.
- **Word choice:** "journey," not "road." Journey vs. destination.

---

## Source quotes (exact, with citations)

### Load-bearing

**Margaret-Anne Storey — the Triple Debt model.** "From Technical Debt to Cognitive and Intent Debt: Rethinking Software Health in the Age of AI," ACM Queue / arXiv 2603.22106 (out of Fowler's Thoughtworks "Future of Software Development" retreat, Feb 2026). [queue.acm.org/detail.cfm?id=3807966](https://queue.acm.org/detail.cfm?id=3807966) · [arxiv.org/abs/2603.22106](https://arxiv.org/abs/2603.22106)
- Intent debt = *"the absence of externalized rationale that developers and AI agents need to work safely with code."* ← note "developers **and** AI agents" — the both-audiences point.
- The three debts by where each lives: **technical** (in the code / changeability), **cognitive** (in people / shared understanding), **intent** (in artifacts / externalized rationale).
- Commentary line: *"AI does not have intent. It does not deliberate."*

**Addy Osmani — "The Intent Debt."** [addyosmani.com/blog/intent-debt/](https://addyosmani.com/blog/intent-debt/)
- *"An agent can't generate intent, because intent is the one input that has to come from you."*
- *"Bringing agents onto a team doubles its size overnight with junior people who have no long-term memory."*
- A model *"will invent a confident-sounding reason, which is worse than admitting it doesn't know."*

**Dheer — "Your ticket is a prompt."** [dheer.co/tickets-are-prompts/](https://dheer.co/tickets-are-prompts/)
- *"Agents don't have hallways."*
- Humans hid the fragmentation by *"catching context in hallway conversations and filling gaps from tribal knowledge."*
- Left unfixed, *"the original outcome was buried under atomic fixes that collectively solved nothing."*

**a16z (David Haber) — "Everything Is Recorded Now."** [a16z.news/p/everything-is-recorded-now](https://www.a16z.news/p/everything-is-recorded-now)
- The bull case: onboard your AI like an employee, let it *"reason over every interaction and never get bored,"* turning voice into something *"structured, searchable, and queryable."*
- The candor-paradox critique (from its own comments): *"Once people assume every meeting is recorded… the messy, half-formed thinking that actually produces good decisions tends to migrate to the hallway and the DM. You capture more context, but a thinner, more performed version of it."*

### Supporting / likely useful

**Thorsten Ball — "Building Software Is Learning."** [registerspill.thorstenball.com/p/building-software-is-learning](https://registerspill.thorstenball.com/p/building-software-is-learning)
- *"building new software is learning."* — pure Naur; the case that intent emerges *during* building, not before. (Useful for §2's fractal point and §6's learning-capture gap.)

**Matt Rickard — "The Spec Layer."** [blog.matt-rickard.com/p/the-spec-layer](https://blog.matt-rickard.com/p/the-spec-layer)
- *"When a decision isn't written down, the agent has to decide it again."*
- Agents fail by producing *"the wrong kind of correct."*

**Tim Kellogg — "Agent Memory Patterns."** [timkellogg.me/blog/2026/04/27/memory-patterns](https://timkellogg.me/blog/2026/04/27/memory-patterns)
- *"the only structure LLMs need is tokens. They reason just fine in token space."* — the structure-vs-tokens challenge (§4 optional half-line; seed-170).

**Meta Engineering — "How Meta Used AI to Map Tribal Knowledge."** [engineering.fb.com/2026/04/06/...](https://engineering.fb.com/2026/04/06/developer-tools/how-meta-used-ai-to-map-tribal-knowledge-in-large-scale-data-pipelines/)
- *"context that decays is worse than no context at all."* (§6 staleness frontier)
- *"compass, not encyclopedia"* — the compact context-file shape.

**Read.ai — on transcription overhead.**
- *"a raw transcript is a starting point, not a solution."* — even vendors concede capture ≠ intent.

**Naur — "Programming as Theory Building" (1985).** The root: a program is a *theory* living in developers' minds, not its source code. The intellectual ancestor of the whole conversation.

### Internal anchors (from the seed-169 investigation — for §4)

- *"Beads represent work; seeds carry the deliberation."* (the `seeds-to-beads` skill)
- The bead carries a **`## Why`** + pre-written content *"so the executing agent doesn't have to re-design,"* plus a `Source: seeds-X` citation. (~37/83 beads carry one.)
- The `bead-process` implementer skill **never tells the agent to read the cited seed** — the citation is a "might need" fallback, not the primary channel.
- Ryan, on why intent is downstream (seed-168): *"you don't figure out what you're trying to do until you've talked about and deliberated what you're trying to do."*

---

## The outline

### 0. Orientation *(short)*
*Ballpark for someone who didn't read the intro post — no rigid taxonomy.*
- The world: solo / small-team dev, AI does the building, conversations (AI chats, Zoom) are transcribed.
- What seeds is, functionally — **not** "the third leg after planning and execution." Say it plainly: *a place to think a feature all the way through before it's built, which then feeds the execution tracker (beads).* Largely a planning tool that feeds execution. Save the "upstream of intent" reveal for §2.

### 1. The conversation named something real
*Credit the field — humbly, spotlight on the tool, not on me.*
- Name it: Storey's *intent debt*; Osmani's *"an agent can't generate intent — it's the one input that has to come from you"*; capture is cheap now, intent is the scarce thing.
- The humble framing (not "I was already operating on the premise"): *while the field was naming this, I'd been **exploring** the same territory with beads — and that exploration is what turned into seeds.*
- The turn: *but I'd push back on letting its vocabulary set the terms for seeds.* (→ §2)

### 2. Intent is the wrong unit — seeds is *upstream* of it
*The thesis. Decline the banner (seed-167), plant seed-168.*
- Core line: **intent is the residue after the rejected branches are resolved away; the deliberation is the only place those branches survive.** Intent sits "further to the right" — more downstream, more settled.
- The three pains (near-verbatim): hate revisiting an old idea as if it's *new*; hate re-loving an idea I already dismissed; and even when I know I dismissed it — *why?* That's nowhere in "intent."
- Why-decisions-*changed*: the guard clause that went in and later came out; the 2023 incident that changed minds — *and the resolutions that were considered and rejected.*
- **The fractal point (core, not optional):** seeds asks not just *what* you want but *how* — and the two are conflated. What's easy in one language/framework and not another genuinely shapes the tool you build (*"less so with generative AI, but not zero"*). You hold an intent while the *how* stays open, and each sub-decision has its own intent underneath. seeds captures each layer; intent-debt framing flattens them.
- Say the boundary out loud: *I'm deliberately not flying the "intent debt" flag — not because it's wrong, but because it names the destination, and seeds is about the journey to it.*

### 3. The trust paradox — and the scale I actually work at
*The personal hook, honestly bounded.*
- The contradiction, flat: I let an AI write **all** my code and commit it **sight-unseen**; I take its design recommendations. **And I won't lean on it to make mid-implementation judgment calls about how a feature should behave.**
- Undercut the absolutism (keep — it's true): it's not a wall. It *does* make behavior decisions; sometimes I adjust them, sometimes I don't.
- What actually makes me secure: not handing the AI my *intent* — having had **a good planning session about what the feature should do.**
- **Scope caveat:** I'm not running a swarm. One feature at a time; a single agent builds it in sequence over an hour or two. *Considerably* more productive than before — not the "1000x" the hype promises, and maybe my scope is too limited. Intent might matter more to a swarm figuring out a product together; I'm not personally ready for that, and I'm not sure the tools are either — *though I'm regularly surprised by what AI turns out to be ready for.*

### 4. So does the agent even need my intent? I checked.
*The evidenced heart — the seed-169 investigation.*
- Frame: the field increasingly treats captured intent as **fuel for the implementing agent** (*"agents don't have hallways"* → give them the hallway). I'd never verified whether the intent I record reaches *my* agents — so I traced the seeds → beads → implementation pipeline.
- The finding (seeds-169 / 171 / 172 / 173): **intent reaches the implementer — but distilled into the bead, not by the agent reading the deliberation.** The hand-off splits cleanly — *"beads represent work; seeds carry the deliberation."* The bead gets the actionable **`## Why`** + a `Source:` citation; the implementer is **never told to follow it back.** The journey stays in the seed.
- The payoff — this dissolves the paradox: *I don't have to trust the AI to interpret my intent mid-build, because the figuring-out is front-loaded into the bead before the agent ever runs.* The agent consumes the **distillation**; the **journey is for me** (and future-me, via an agent reconstructing it on demand — "why SQLite? why JSONL export?").
- One-liner: *the field wants to give the agent intent so it can decide well; seeds front-loads the deliberation so the agent never has to decide the things I care about.*
- Name the dependency honestly (sets up §6): it all rides on the **distillation step** — whatever it drops is invisible downstream.
- *[optional half-line]* This quietly answers Kellogg's "does the structure fight the agent?" (seed-170): the agent barely touches seeds' structure — it gets a flat, distilled bead. The structure serves *me and the history,* not the model.

### 5. Why this works in my world
*Pre-empt the obvious objections (seeds-165, 166).*
- **The candor paradox doesn't bite me — and where it does, it's a feature (seed-165):** there are *no hallways* in my work — AI collaboration or recorded Zoom, on the record by design, because my boss and I *want* the decisions recorded. Knowing it's captured makes me *more* deliberate: I'll say "note this," flag what matters — small, useful direction to a future agent. And *isn't talk at work already a bit performative?* The bar isn't raw candor, it's **tactfully candid.** seeds is the *antidote* to ambient recording: where deliberation is *conducted intentionally and in the loop,* not ambiently surveilled.
- **I don't reconstruct intent from residue — it's a fidelity call (seed-166):** I deliberately don't back-infer the decisions on my decades-old system. Not mainly because they're lost to time — because **live capture is higher-fidelity than anything I could reconstruct.** LLM transcription and LLM collaboration give me rich, in-the-moment capture; old code, git history, the odd surviving email don't come close to the rigor of a transcribed working session. I'm not interested in lower-fidelity sources *right now.* (Maybe someday I'll mine the old system — not today.)

### 6. The honest gaps
*End on candor (seed-161 + the self-audit family). Don't overclaim.*
- **The distillation is the single point of failure.** Everything good about the pipeline depends on the seed → bead compression being faithful. First place I'd look if the magic broke.
- **Learning-capture is thinner than I'd like (seed-161)** — *with the softener:* I'm strong on the prescriptive plant-and-explore phase, weaker on "what did we *learn* by trying it." But a lot of the learning already happens *in the deliberation,* and by build time I usually have a firm handle — so far the decisions have held, so the gap is real but **not yet painful.** ("Not claiming perfect software; we'll see.")
- *[optional — the frontier I'm circling, seeds-158/159/160]:* the dark twin of "the deliberation survives" is *does it stay true?* Resolved decisions can **age out,** or two resolutions made months apart can **contradict** each other. I'm poking at whether seeds should audit its own body of knowledge — warily: it's journey-capture, not a freshness monitor, and outcome-tracking risks becoming *"a heavy chore with questionable value."* Name it open, not solved.
- **Longevity unproven.** Five months old. Everything here is "true so far."

### 7. Close
- *seeds is upstream of intent.* Conduct the deliberation, distill *what to build* before the agent runs, and keep the journey — the discarded branches and the changed minds — not just the destination. The field is racing to feed agents intent; I'm front-loading the thinking so the agent doesn't need it, and keeping the journey for the one reader who does: me, later.

---

## Open forks (your call)

- **Opening:** orientation-first (§0 → §1), per Mark Danese's "set the ballpark" note. The trust-paradox cold-open (lead with §3's contradiction, orient second) is still available if you want a harder hook.
- **§4 as climax vs. open question:** the investigation resolved, so this leads with the finding. If you'd rather preserve an "I don't fully know" texture, soften seed-169 back toward open — but the finding is the stronger, more honest move.
- **Self-audit frontier (§6 optional bullet):** included lightly. Cut if it pulls focus from the positioning.
