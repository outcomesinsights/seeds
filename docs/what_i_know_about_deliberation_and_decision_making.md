# What I Know About Deliberation and Decision-Making

**Created:** 2026-01-22
**Context:** Research for ADRB tooling - capturing the *process* of reaching decisions, not just the final decision record

---

## Table of Contents

1. [Core Concepts and Definitions](#core-concepts-and-definitions)
2. [Decision-Making Frameworks](#decision-making-frameworks)
3. [Deliberation: Structure and Methods](#deliberation-structure-and-methods)
4. [Documentation Patterns and Artifacts](#documentation-patterns-and-artifacts)
5. [Questions and Answers as Deliberation Artifacts](#questions-and-answers-as-deliberation-artifacts)
6. [Tools and Systems](#tools-and-systems)
7. [Human+AI Deliberation](#humanai-deliberation)
8. [Best Practices](#best-practices)
9. [Anti-Patterns](#anti-patterns)
10. [How This Relates to RFCs, ADRs, and Design Docs](#how-this-relates-to-rfcs-adrs-and-design-docs)
11. [Synthesis: What We Need](#synthesis-what-we-need)
12. [Sources and Further Reading](#sources-and-further-reading)

---

## Core Concepts and Definitions

### What is Deliberation?

Deliberation is the process of carefully weighing options before making a decision. It involves:

- **Exploring alternatives**: Identifying possible courses of action
- **Gathering information**: Understanding the context and constraints
- **Weighing trade-offs**: Evaluating pros and cons of each option
- **Incorporating multiple perspectives**: Considering different viewpoints
- **Reaching a conclusion**: Arriving at a decision that can be justified

Deliberation is distinct from simply *making* a decision. It is the *journey* to that decision.

### Wicked Problems

The concept of "wicked problems" is foundational to understanding why deliberation matters. Introduced by Horst Rittel and Melvin Webber in 1973, wicked problems are characterized by:

- No definitive formulation of the problem
- No stopping rule (no way to know when you're done)
- Solutions are not true-or-false, only good-or-bad
- No immediate or ultimate test of a solution
- Every solution is a "one-shot operation" with consequences
- No enumerable set of potential solutions
- Every wicked problem is essentially unique

Software architecture decisions often exhibit "wickedness" - they involve trade-offs, have no objectively correct answer, and their consequences play out over time.

### Dialogue vs. Deliberation

These terms are often conflated but serve different purposes:

| Dialogue | Deliberation |
|----------|--------------|
| Fosters understanding and connection | Guides toward decisions and outcomes |
| Open-ended exploration | Structured toward resolution |
| Values meaning-making | Values actionable conclusions |
| No predetermined goal | Aims at consensus or decision |

Both have a place in the decision-making lifecycle. Dialogue often precedes deliberation.

---

## Decision-Making Frameworks

### RAPID (Bain & Company)

RAPID is a decision-making framework that clarifies who does what:

- **R**ecommend: Gathers input, develops recommendations
- **A**gree: Must agree the recommendation is feasible (often legal/regulatory)
- **P**erform: Executes the decision once made
- **I**nput: Provides information and perspectives
- **D**ecide: Makes the final call

**Key insight**: Despite the name, RAPID isn't about speed - it's about *clarity*. It works best for complex decisions requiring multiple stakeholders.

### RACI (Responsibility Assignment)

RACI is task-centric (vs. RAPID which is decision-centric):

- **R**esponsible: Does the work
- **A**ccountable: Ultimately answerable
- **C**onsulted: Provides input before the work
- **I**nformed: Kept up to date

**When to use each**: Use RAPID to decide *what* to do, then RACI to assign *how* to execute.

### DACI (Atlassian's Variant)

- **D**river: Gathers information, runs the process
- **A**pprover: Makes the final decision
- **C**ontributors: Provide expertise and input
- **I**nformed: Notified of the outcome

DACI works well for asynchronous decision-making because it establishes clear roles and timelines upfront.

### Consent-Based Decision-Making (Sociocracy/Holacracy)

Instead of seeking agreement ("Does everyone agree?"), consent-based approaches ask: "Are there any objections?"

The definition of an objection: "Carrying out this proposal will interfere with our ability to achieve our aims."

The process:
1. Present proposal
2. Clarifying questions
3. Reaction round
4. Amend and clarify
5. Objection round (objections are tested)
6. Integration round (resolve objections by modifying the proposal)

**Key insight**: The "range of tolerance" - decisions don't need everyone's enthusiasm, just the absence of reasoned objections.

### The Advice Process

Used in self-managing organizations:

1. Anyone can make a decision
2. Before deciding, they must seek advice from:
   - People who will be affected
   - People with expertise

The decision-maker is not obligated to follow the advice, but must genuinely consider it.

**Key insight**: This balances autonomy with collective wisdom. It's lightweight for small decisions, thorough for big ones.

### Structured Decision Making (SDM)

From the decision sciences, SDM provides a framework for complex decisions:

1. Clarify objectives (what matters?)
2. Identify alternatives (what could we do?)
3. Evaluate consequences (what happens with each alternative?)
4. Evaluate trade-offs (how do we weight competing objectives?)
5. Implement and monitor

**Key insight**: SDM makes values explicit. Disagreements often stem from different unstated objectives.

---

## Deliberation: Structure and Methods

### IBIS: Issue-Based Information Systems

Developed by Werner Kunz and Horst Rittel in the 1960s, IBIS provides a grammar for deliberation:

**Elements:**
- **Issues** (Questions): What needs to be decided?
- **Positions** (Ideas): What are the possible answers?
- **Arguments**: Why support or oppose a position?
  - **Pros**: Arguments supporting a position
  - **Cons**: Arguments opposing a position

IBIS creates a graph structure that captures the reasoning behind decisions. It was designed specifically to support deliberation on wicked problems.

### Dialogue Mapping

Created by Jeff Conklin in the 1990s, dialogue mapping is a facilitation technique that uses IBIS in real-time:

- A facilitator ("info-cartographer") captures discussion on a shared display
- Uses IBIS notation to structure contributions
- Creates a visual record of the group's thinking
- Prevents "wheel spinning" by making the discussion visible

**Key insight**: Once an idea is mapped, it's taken seriously. This reduces repetition and ensures all voices are captured.

### QOC: Questions, Options, and Criteria

Developed at Rank Xerox EuroPARC, QOC structures design rationale:

- **Questions**: What needs to be decided?
- **Options**: What are the alternatives?
- **Criteria**: What matters in evaluating options?

Options are evaluated against criteria, making trade-offs explicit.

### The Socratic Method

Structured questioning to explore ideas:

1. **Clarifying concepts**: What do we mean by X?
2. **Examining assumptions**: Why do we believe that?
3. **Seeking evidence**: What supports this view?
4. **Exploring implications**: What follows from this?

The Socratic method is iterative - each answer generates new questions.

**Key insight for human+AI work**: The Socratic method can structure interaction between a human and AI assistant, with either party asking probing questions.

### Synchronous vs. Asynchronous Deliberation

| Synchronous | Asynchronous |
|-------------|--------------|
| Real-time meetings | Distributed over time |
| Benefits from energy and momentum | Allows time for reflection |
| Risk of groupthink | Reduces bias from social pressure |
| Harder across time zones | Enables global participation |
| Favors quick thinkers | Levels the playing field |

**Best practice for async deliberation:**
- Use a central communication channel with threading
- Establish clear timelines and decision-makers (DACI)
- Document decisions in an accessible source of truth
- Broadcast outcomes to all stakeholders

The Apache Software Foundation uses async deliberation to allow 9 board members to make dozens of decisions in less than 2 hours of monthly meetings - by doing most deliberation asynchronously in advance.

---

## Documentation Patterns and Artifacts

### The Spectrum of Decision Documentation

Different artifacts capture different aspects of the decision lifecycle:

| Artifact | When Written | Purpose | Captures Journey? |
|----------|--------------|---------|-------------------|
| Meeting notes/transcripts | During/after discussion | Record of conversation | Yes (raw) |
| RFC/Design Doc | Before implementation | Propose approach, get feedback | Partially |
| Decision Journal | At decision time | Personal reflection | Yes |
| ADR | After decision | Record decision and rationale | Summary only |
| Decision Log | Ongoing | Track project decisions | No |

### Decision Journals (Personal)

A decision journal is a personal record for improving decision quality over time.

**What to capture:**
- The decision being made
- The date and your mental/emotional state
- Expected outcomes and confidence levels
- Key factors considered
- Alternatives rejected and why
- What would change your mind

**Why it matters**: Hindsight bias distorts memory. A decision journal preserves what you actually knew and thought at the time, enabling honest retrospectives.

**Key insight**: Decision journals are about *process* improvement, not just documentation. Reviewing them reveals patterns in your thinking.

### Decision Logs (Project)

A decision log tracks decisions within a project:

- What was decided
- Who decided it
- When it was decided
- Brief rationale
- Impact on project

Decision logs are lighter than ADRs - they document *that* a decision was made without deep rationale.

### Design Rationale

Design rationale captures why a system is designed the way it is:

- Issues addressed
- Options considered
- Arguments for/against each option
- How the final choice was made

**The challenge**: Capturing design rationale adds effort. The benefit comes later (during maintenance, redesign, or onboarding), creating a motivation gap.

**Tools like DRed** (Design Rationale editor) try to make capture lightweight enough to be practical.

### Transcripts and Raw Captures

With AI transcription becoming ubiquitous, raw conversation transcripts are increasingly available. They capture:

- The full context of discussion
- Questions asked along the way
- How understanding evolved
- Dissenting views that didn't make the final record

**Key insight from immediateissues.md**: "My boss and I transcribe all of our conversations now." This creates raw material that could be processed into structured artifacts.

---

## Questions and Answers as Deliberation Artifacts

### Q&A as First-Class Entities

From the ADRB discovery process, a key insight emerged: questions and answers could be tracked as separate entities:

- **One ADR generates many questions**
- **One question may have many answers** (from different sources, perspectives, or models)

This creates a deliberation record that captures the journey to understanding.

### Structured Inquiry Patterns

Several patterns use questions as organizing principles:

**Socratic questioning** proceeds through types:
1. Conceptual clarification questions
2. Probing assumptions
3. Probing rationale, reasons, evidence
4. Questioning viewpoints and perspectives
5. Probing implications and consequences
6. Questions about the question

**IBIS** treats questions (issues) as primary:
- Questions decompose into sub-questions
- Questions are answered by positions
- Positions are supported/opposed by arguments

### Multiple Perspectives on the Same Question

A question can receive answers from:
- Different team members (human perspectives)
- Different LLMs (model perspectives)
- The same person at different times (temporal perspectives)
- Different roles (stakeholder perspectives)

**Key insight**: Tracking multiple answers to the same question creates a richer deliberation record than converging to a single answer too quickly.

---

## Tools and Systems

### Argument Visualization Tools

**Compendium**
- Open-source IBIS-based tool
- Supports dialogue mapping
- Creates visual maps of issues, positions, arguments
- No longer actively maintained but still available

**DRed (Design Rationale Editor)**
- Developed at Cambridge Engineering Design Centre
- IBIS-based with color-coded status (amber=open, green=resolved)
- Designed for engineers capturing design rationale

**Vithanco**
- Modern tool supporting IBIS notation
- Creates argument maps

### Collaborative Decision Platforms

**Loomio**
- Open-source decision-making software
- Supports proposals, discussions, and voting
- Built by a worker-owned cooperative
- Used by governments, organizations, and movements
- Designed for consent-based decision-making

**Miro/FigJam/Whiteboard tools**
- General-purpose but used for dialogue mapping
- Design rationale often captured as sticky notes
- Less structured than purpose-built tools

### Async Collaboration Tools

**Notion/Confluence**
- RFCs and design docs often live here
- Comments enable async deliberation
- Lack structure for IBIS-style argumentation

**GitHub Discussions/Issues**
- RFC workflows often use GitHub
- Threaded discussions
- Can link to code and PRs

### Decision Support Systems (DSS)

Enterprise decision support systems focus on data analysis for decisions. They're typically:
- Data-driven (analytics, dashboards)
- Focused on business decisions
- Less about capturing deliberation, more about informing it

---

## Human+AI Deliberation

### How AI Changes Deliberation

Working with an AI assistant fundamentally changes the deliberation dynamic:

**Availability**: The AI is always available for discussion
**Persistence**: But conversations are often ephemeral
**Knowledge**: Broad knowledge, but can hallucinate
**Perspective**: Different "thinking style" than humans
**Patience**: Unlimited capacity for iteration

**Key insight from immediateissues.md**: "Discussion happens in ephemeral Claude sessions. There's no persistent place to capture 'I have questions about this.'"

### Emerging Paradigms

Research is revealing new patterns for human-AI collaboration:

**Learning to Guide**: Rather than the AI simply recommending or deferring, it provides "hints" to help humans make better decisions themselves. This avoids both automation bias (over-reliance on AI) and leaving humans unassisted.

**Human-AI Deliberation**: The AI provides recommendations with explanations, but humans evaluate through discussion of conflicts between human and AI opinions. This promotes understanding rather than blind acceptance.

**AI as Reasoning Facilitator**: The AI-Supported Shared Decision-Making (AI-SDM) framework positions AI as a facilitator of reasoning, not a decision-maker. AI insights are transparent, contestable, and tailored.

### Multi-LLM Deliberation

Different LLMs have different "perspectives" due to different training:

**LLM Council** (Andrej Karpathy): Multiple models answer, critique each other anonymously, and a "chairman" model synthesizes a final answer.

**Adaptive Heterogeneous Multi-Agent Debate**: Specialized agents (e.g., Verifier, Solver) debate to improve accuracy. Achieved 4-6% accuracy gains and 30% reduction in factual errors.

**Co-LLM** (MIT): A general-purpose model calls on specialized models for specific domains.

**Key insight**: Just as diverse human teams outperform homogeneous ones, diverse LLM ensembles can outperform single models.

### Capturing AI-Generated Insights

When working with AI, valuable content is generated that should be captured:

- Questions the AI asked that revealed blind spots
- Alternatives the AI suggested that weren't obvious
- Reasoning chains that led to insights
- Disagreements between human and AI that were resolved

**The problem**: These insights live in chat transcripts that are hard to search and easy to lose.

### The Human+AI Pair Workflow

For a human working closely with an AI assistant:

1. **Exploration phase**: Dialogue with AI to understand the problem space
2. **Deliberation phase**: Structured consideration of alternatives
3. **Decision phase**: Human makes the final call
4. **Documentation phase**: Capture the decision and key insights

**Gap identified**: Current tools support steps 1 and 4 poorly for human+AI pairs:
- Exploration happens in ephemeral sessions
- Documentation captures outcomes, not journeys

---

## Best Practices

### For Effective Deliberation

1. **Make the question explicit**: Unclear questions lead to unclear decisions. Use IBIS-style framing.

2. **Separate divergent and convergent phases**: First explore broadly, then narrow down. Trying to converge too early kills good ideas.

3. **Externalize reasoning**: Write it down. Draw it. The act of externalization reveals gaps and assumptions.

4. **Seek dissent actively**: Ask "What could go wrong?" and "Who disagrees?" Assign a devil's advocate role.

5. **Track alternatives considered**: Future you will want to know why you didn't choose Option B.

6. **Time-box appropriately**: Some decisions deserve weeks; others deserve minutes. Match the process to the stakes.

7. **Use async for reflection, sync for energy**: Complex reasoning benefits from async. Building shared understanding benefits from sync.

### For Documentation

1. **Capture at the moment of decision**: Memory decays rapidly. Document when the context is fresh.

2. **Include emotional/contextual state**: Stress, time pressure, and incomplete information affect decisions. Record these.

3. **Write for your future self**: You won't remember the context. Explain it as if to a stranger.

4. **Link to source material**: Reference the meeting transcript, the data analysis, the RFC discussion.

5. **Keep it lightweight enough to actually do**: A documentation practice you don't follow is worthless.

### For Human+AI Collaboration

1. **Save key exchanges**: When the AI asks a great question or surfaces a key insight, capture it.

2. **Maintain continuity**: Start new sessions with context from previous ones. Use persistent notes.

3. **Ask the AI to challenge you**: "What am I missing?" "Argue the opposite position."

4. **Leverage different models**: Different LLMs have different strengths. Use them for different perspectives.

5. **Document disagreements**: When you and the AI disagree, that's often where the interesting reasoning lives.

---

## Anti-Patterns

### Decision-Making Failures

**Anchoring Bias**: The first number/option mentioned dominates thinking. Mitigate by generating multiple options before evaluating any.

**Confirmation Bias**: Seeking evidence that supports existing beliefs. Mitigate by explicitly seeking disconfirming evidence.

**Sunk Cost Fallacy**: Continuing because of past investment, not future value. Mitigate by asking "If we were starting fresh, would we choose this?"

**Plan Continuation Bias**: Sticking with the original plan when circumstances have changed. Mitigate by explicit checkpoints to reconsider.

**Groupthink**: Converging on consensus without genuine evaluation. Mitigate by structured dissent, anonymous input, or async deliberation.

**Analysis Paralysis**: Over-deliberating, never deciding. Mitigate by setting decision deadlines and "good enough" criteria.

**HiPPO** (Highest Paid Person's Opinion): Deferring to seniority rather than reasoning. Mitigate with frameworks like RAPID that clarify roles.

### Documentation Failures

**Writing for the record, not understanding**: Documents that satisfy process requirements but don't actually help anyone understand.

**Premature documentation**: Capturing decisions before they've actually been made, cementing half-baked thinking.

**Documentation debt**: Letting artifacts become stale. An outdated ADR is worse than no ADR.

**Over-documentation**: Capturing everything, making nothing findable. The signal-to-noise ratio matters.

**Hindsight reconstruction**: Writing rationale after the fact, inventing reasons that weren't actually considered. Keep raw artifacts to stay honest.

### Human+AI Collaboration Failures

**Over-reliance on AI**: Accepting AI output without critical evaluation. The AI can be confidently wrong.

**Under-reliance on AI**: Dismissing AI input that challenges human assumptions. The AI may see things humans miss.

**Ephemeral exploration**: Having valuable discussions with AI that are never captured. Insights are lost.

**Context loss**: Starting each AI session from scratch without providing relevant history. Wastes time and loses continuity.

---

## How This Relates to RFCs, ADRs, and Design Docs

### The Landscape of Engineering Documentation

| Document Type | Purpose | When Written | Feedback? | Captures Process? |
|--------------|---------|--------------|-----------|-------------------|
| RFC | Propose approach, solicit comments | Before implementation | Yes, primary purpose | Partially (comments) |
| Design Doc | Detail technical approach | Before implementation | Yes | Partially (comments) |
| ADR | Record architectural decision | At/after decision | Minimal | Summary of rationale |
| Decision Log | Track project decisions | Ongoing | No | No |
| Meeting Notes | Record discussion | During/after meeting | No | Yes (raw) |

### The Gap

None of these cleanly capture the *exploration* phase:
- The questions that arose and how they were answered
- The alternatives that were considered seriously
- The reasoning that led to narrowing down options
- The dissent and how it was addressed

RFCs come closest, as they invite comments. But RFC comments are often about the *proposal*, not the journey to the proposal.

### What ADRB Could Become

From immediateissues.md: "A tool that its ultimate product is an ADR, but captures the thinking that went in, the exploration and thinking that went in to the process before the ADR was generated and set in stone."

This would fill the gap between:
- Raw discussion (meeting transcripts, chat logs) - too unstructured
- Final artifacts (ADRs, Design Docs) - too polished, no journey

### Possible Relationships

```
Transcripts/Chat Logs
        |
        v
[Exploration Tool] <-- captures questions, answers, alternatives
        |
        v
    RFC/Design Doc <-- proposed approach
        |
        v
      ADR <-- final decision record
```

The "Exploration Tool" (what ADRB might become) would:
- Track questions and their answers
- Capture alternatives considered
- Allow multiple perspectives per question
- Link to source material (transcripts, etc.)
- Eventually generate or feed into ADRs

---

## Synthesis: What We Need

Based on this research, here's what a deliberation support tool for human+AI pairs might need:

### Core Features

1. **Question tracking**: First-class entities for questions/issues that arise during exploration

2. **Multi-answer support**: A question can have multiple answers from different sources (human, different LLMs, over time)

3. **IBIS-style argumentation**: Support for capturing pros, cons, and supporting arguments

4. **Source linking**: Connect insights to their origins (chat logs, transcripts, documents)

5. **Status tracking**: What's open, what's resolved, what's deferred

6. **ADR generation**: Ability to synthesize exploration artifacts into a final ADR

### Design Principles

1. **Lightweight capture**: Must be easy enough to actually use during exploration

2. **Structured enough to be useful**: Not just a text dump, but queryable/navigable

3. **Preserves the journey**: Don't lose the path to the decision

4. **Supports async**: Human+AI pairs work across sessions, not just real-time

5. **Handles uncertainty**: "I have questions about this" is a valid state

### Open Questions

1. Should exploration artifacts live in ADRB, Beads, or a new tool?

2. How do we prevent the exploration tool from becoming a documentation graveyard?

3. What's the right level of structure vs. freeform capture?

4. How do we import/link to external sources (chat logs, transcripts)?

5. What triggers moving from exploration to decision?

---

## Sources and Further Reading

### Decision-Making Frameworks
- [DACI Framework - Atlassian](https://www.atlassian.com/team-playbook/plays/daci)
- [RAPID Decision Making - Bain & Company](https://www.bain.com/insights/rapid-decision-making/)
- [RAPID vs RACI - Indeed](https://www.indeed.com/career-advice/career-development/rapid-vs-raci)
- [Structured Decision Making](https://www.structureddecisionmaking.org/)
- [AI-Supported Shared Decision-Making Framework](https://pmc.ncbi.nlm.nih.gov/articles/PMC12331219/)

### Deliberation and Argumentation
- [Issue-Based Information Systems - Wikipedia](https://en.wikipedia.org/wiki/Issue-based_information_system)
- [IBIS: A Tool for All Reasons](http://www.cognexus.org/IBIS-A_Tool_for_All_Reasons.pdf)
- [Dialogue Mapping - Lucidchart](https://www.lucidchart.com/blog/what-is-dialogue-mapping)
- [The IBIS Notation - Vithanco](https://vithanco.com/notations/IBIS/index/)
- [Design Rationale - Wikipedia](https://en.wikipedia.org/wiki/Design_rationale)

### Consent and Collaborative Decision-Making
- [Consent Decision Making - Sociocracy For All](https://www.sociocracyforall.org/consent-decision-making/)
- [Consent Decision-Making - Sociocracy 3.0](https://patterns.sociocracy30.org/consent-decision-making.html)
- [Comparing Decision-Making Methods](https://www.corporate-rebels.com/blog/comparing-decision-making-methods)

### Decision Journals and Logs
- [Decision Journal - Farnam Street](https://fs.blog/decision-journal/)
- [Decision Journal - Alliance for Decision Education](https://alliancefordecisioneducation.org/resources/keeping-a-decision-journal/)
- [Decision Journal - Atlassian](https://www.atlassian.com/blog/productivity/decision-journal)
- [Decision Log - Lucid Meetings](https://www.lucidmeetings.com/glossary/decision-log)

### RFCs and Design Docs
- [Engineering Planning with RFCs, Design Documents and ADRs - Pragmatic Engineer](https://newsletter.pragmaticengineer.com/p/rfcs-and-design-docs)
- [Software Engineering RFC and Design Doc Examples](https://newsletter.pragmaticengineer.com/p/software-engineering-rfc-and-design)
- [RFC Guide - Medium](https://medium.com/juans-and-zeroes/a-thorough-team-guide-to-rfcs-8aa14f8e757c)

### Human+AI Collaboration
- [Fostering Effective Hybrid Human-LLM Reasoning](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2024.1464690/full)
- [Multi-AI Collaboration - MIT News](https://news.mit.edu/2023/multi-ai-collaboration-helps-reasoning-factual-accuracy-language-models-0918)
- [Human-AI Deliberation Research](https://arxiv.org/html/2403.16812v1)
- [LLM Council](https://llm-council.dev/)
- [AI-Powered Collaboration Models](https://www.augmentcode.com/guides/6-ai-human-development-collaboration-models-that-work)

### Asynchronous Decision-Making
- [Asynchronous Decision-Making - Opensource.com](https://opensource.com/article/17/12/asynchronous-decision-making)
- [Async Decisions for Remote Teams - Slite](https://slite.com/blog/how-to-make-decisions-asynchronously)
- [Async Practices - Atlassian](https://www.atlassian.com/blog/teamwork/async-practices-for-decision-making)

### Wicked Problems
- [Wicked Problems - Wikipedia](https://en.wikipedia.org/wiki/Wicked_problem)
- [Understanding Wicked Problems - Systems Thinking Alliance](https://systemsthinkingalliance.org/wicked-problems/)
- [Wicked Problems in Design Thinking](https://www.interaction-design.org/literature/topics/wicked-problems)

### Cognitive Bias and Anti-Patterns
- [Cognitive Biases in Decision Making](https://pmc.ncbi.nlm.nih.gov/articles/PMC8763848/)
- [Cognitive Bias - Wikipedia](https://en.wikipedia.org/wiki/Cognitive_bias)
- [Cognitive Biases in Board Decision-Making](https://www.boardpro.com/blog/cognitive-biases-in-board-decision-making)

### Tools
- [Compendium Software](https://en.wikipedia.org/wiki/Compendium_(software))
- [Loomio](https://www.loomio.com/)
- [Socratic Questioning - Wikipedia](https://en.wikipedia.org/wiki/Socratic_questioning)

---

*This document captures research to inform the development of tools that support the decision-making process, not just the decision record. It emerged from the realization in immediateissues.md that ADRs capture outcomes, not journeys, and that human+AI pairs need tooling to support their unique deliberation workflow.*
