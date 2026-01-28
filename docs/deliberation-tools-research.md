# Deliberation & Decision-Making Tools Research

**Created:** 2026-01-27
**Purpose:** Survey of tools that might provide the SEEDS vision - capturing the deliberation process, nurturing ideas from seed to fruit

---

## Executive Summary

After extensive research, **no existing tool fully matches the SEEDS vision**. However, several tools address parts of it, and combining insights from multiple categories could inform SEEDS design.

### The Gap

Your vision has unique requirements that no single tool addresses:
1. **Active deliberation support** (not just passive capture)
2. **Ideas as first-class entities** with lifecycle (seed → fruit)
3. **Questions/answers as structured objects** attached to ideas
4. **Explicit backlog/deferral** for ideas not ready to explore
5. **Mind-racing support** - quick capture of tangential thoughts
6. **AI agent-friendly** - designed for human-AI collaboration
7. **Domain agnostic** - software, RPGs, house projects, life decisions

### Closest Matches (Partial)

| Tool | What It Gets Right | What's Missing |
|------|-------------------|----------------|
| **Intent.build** | Captures AI session decisions, preserves reasoning | Passive capture, no active deliberation support |
| **Argdown** | Text-based argumentation, version-controllable | No idea lifecycle, no backlog, no AI integration |
| **Tana** | Structured nodes, AI integration, flexible tagging | Enterprise-focused, not deliberation-centric |
| **Roam Research** | Block-level thinking, daily notes, networked thought | Development stalled, no deliberation workflow |
| **Decision Journal App** | Tracks reasoning and outcomes | Personal journaling only, no idea relationships |
| **Kinopio** | Spatial thinking, quick capture, connection cables | No lifecycle states, no Q&A structure |

---

## Category 1: IBIS/Design Rationale Tools (Historical Lineage)

These tools directly address deliberation and decision-making structure. From your decisionTools.markdown research:

### Argdown ⭐ Most Relevant
- **Website:** https://argdown.org/
- **Status:** Active, open source
- **Why it matters:** Markdown-inspired syntax for argumentation. Text-based, version-controllable, fits CLI/git workflows.

**Alignment:**
- ✅ Text-first (git-friendly)
- ✅ Argument mapping (Issues → Positions → Arguments)
- ✅ VS Code and Obsidian plugins
- ❌ No idea lifecycle/backlog
- ❌ No AI integration
- ❌ No question tracking

**Potential:** Could be used for visualization/export of deliberation, but not the primary capture tool.

### Compendium (Historical Reference)
- **Download:** https://cognexus.org/download_compendium.htm
- **Status:** Unmaintained but downloadable (Java)
- **Lineage:** gIBIS → QuestMap → Compendium

The most complete IBIS implementation still available. Worth downloading to understand what a full deliberation tool looks like.

### Kialo / Kialo Edu
- **Website:** https://www.kialo.com/
- **Status:** Active, proprietary
- **Focus:** Argument mapping as debate trees

**Alignment:**
- ✅ Structured pros/cons
- ✅ Web-native, widely used
- ❌ Public debate focus, not personal deliberation
- ❌ No idea backlog concept
- ❌ Not AI-friendly for agent use

### DRed (Design Rationale editor)
- **Status:** Internal to Rolls-Royce, not publicly available
- **Why it matters:** The only IBIS tool that achieved real industrial scale deployment

**Key insight:** DRed succeeded because it was embedded in organizational process. Rationale capture works when it's part of the workflow, not a separate step.

---

## Category 2: Intent Capture Tools

### Intent.build
- **Website:** https://intent.build/
- **Focus:** Capture decisions from AI coding sessions

**From your overview document:**
- Automatic capture from Claude Code, Cursor, Codex, Gemini
- Provenance mapping (code ↔ conversation)
- CRDT-based version history
- "Mindful making" philosophy

**Alignment:**
- ✅ Preserves reasoning that would otherwise be lost
- ✅ Works with AI tools
- ✅ Version history of decisions
- ❌ Passive capture - doesn't support active deliberation
- ❌ Code-centric, not general purpose
- ❌ No idea lifecycle or backlog
- ❌ Captures outcomes, not the journey

**Verdict:** Solves "don't lose decisions" but not "help me deliberate."

### Claude Conversation Logger
- **Concept:** Persistent, searchable memory of Claude sessions
- **Reference:** https://skywork.ai/skypage/en/claude-conversation-logger-ai-engineer/

Transforms Claude from stateless chat to a system with persistent, analyzable memory. Could be useful for SEEDS as underlying storage mechanism.

---

## Category 3: Networked Thought / PKM Tools

These tools excel at connecting ideas but lack deliberation-specific structure.

### Roam Research
- **Website:** https://roamresearch.com/
- **Price:** $15/month (Pro)
- **Status:** Development has slowed significantly

**Alignment:**
- ✅ Block-level thinking (smallest unit = thought)
- ✅ Bi-directional links
- ✅ Daily notes for capture
- ✅ Networked thought model
- ❌ No deliberation workflow
- ❌ No idea lifecycle states
- ❌ No explicit Q&A structure
- ❌ Development concerns

**Historical note:** Roam pioneered many concepts now common across PKM tools.

### Obsidian
- **Website:** https://obsidian.md/
- **Price:** Free for personal use
- **Status:** Active, dominant in PKM space

**Alignment:**
- ✅ Local-first, privacy-focused
- ✅ Massive plugin ecosystem
- ✅ Markdown files (portable, version-controllable)
- ✅ Graph view for connections
- ❌ Page-level focus (not block-level)
- ❌ No built-in deliberation structure
- ❌ Would require custom plugins for SEEDS-like workflow

**Plugin ecosystem includes:** Argdown integration, Dataview for queries, Canvas for spatial thinking.

### Logseq
- **Website:** https://logseq.com/
- **Price:** Free, open source
- **Status:** Active development

**Alignment:**
- ✅ Open source, local-first
- ✅ Outliner with block-level thinking
- ✅ Built-in TODO/LATER workflow states
- ✅ Daily journals for idea capture
- ✅ Query system for finding ideas
- ❌ No deliberation-specific structure
- ❌ Backlog workflow requires manual setup

**Backlog pattern:** Users create `Backlog/<project>` pages with scheduled dates. Plugin `logseq-plugin-refile` helps move items to backlog.

**Closest to SEEDS workflow** among PKM tools due to TODO/LATER states.

### Tana
- **Website:** https://tana.inc/
- **Price:** Subscription model
- **Status:** Active, well-funded

**Alignment:**
- ✅ Node-based (everything is a node)
- ✅ Supertags for structured metadata
- ✅ AI chat with notes as context
- ✅ Flexible tagging system
- ❌ Steep learning curve
- ❌ Enterprise-focused
- ❌ No explicit deliberation workflow

**2025 updates:** New Android app, AI chat built-in, better mobile support.

### Capacities
- **Website:** https://capacities.io/
- **Status:** Active, growing
- **Approach:** Object-based (not page or block)

**Alignment:**
- ✅ Objects as first-class entities
- ✅ Flexible linking
- ✅ Fast performance
- ❌ No deliberation structure
- ❌ No idea lifecycle

**Key concept:** Information organized around "objects" rather than pages or blocks. Closer to how SEEDS might model "ideas."

### Mem AI
- **Website:** https://mem.ai/
- **Status:** Active (Mem 2.0 released Spring 2025)

**Alignment:**
- ✅ AI-first design
- ✅ Automatic organization
- ✅ "Connections" view surfaces related notes
- ❌ No deliberation workflow
- ❌ Development pace has lagged competitors

---

## Category 4: Visual/Spatial Thinking Tools

### Heptabase
- **Website:** https://heptabase.com/
- **Price:** ~$10/month
- **Focus:** Visual knowledge management, research

**Alignment:**
- ✅ Whiteboard-in-whiteboard (nested canvases)
- ✅ Cards as units of thought
- ✅ Bi-directional links between cards
- ✅ PDF annotation integration
- ✅ Local/offline operation
- ❌ No deliberation workflow
- ❌ No idea lifecycle states
- ❌ No mobile apps

**Best for:** Visual researchers who want to map ideas spatially.

### Scrintal
- **Website:** https://scrintal.com/
- **Price:** ~$10/month
- **Focus:** Visual note-taking for researchers

**Similar to Heptabase** with better design, cloud storage, real-time collaboration. Also no mobile apps.

### Kinopio ⭐ Worth Exploring
- **Website:** https://kinopio.club/
- **Price:** $6/month (freemium)
- **Status:** Active, indie project

**Alignment:**
- ✅ Spatial thinking canvas
- ✅ Quick capture (low friction)
- ✅ Connection "cables" between ideas
- ✅ Offline support, no signup required to try
- ✅ Simple, focused design
- ❌ No lifecycle states
- ❌ No Q&A structure
- ❌ Not AI-integrated

**Key insight:** Connection system inspired by modular synthesizers - "patch cables" between ideas. This is close to the idea relationships you described (ideas spawning, splitting, merging).

**Creator background:** Previously at Fog Creek (Trello, Stack Overflow, Glitch).

### Muse
- **Website:** https://museapp.com/
- **Platform:** iPad and Mac only
- **Focus:** Thinking canvas, infinite boards

**Alignment:**
- ✅ Boards can contain boards (nested thinking)
- ✅ Organic growth over time
- ✅ Mixed media (writing, scribbles, PDFs, links)
- ❌ Apple ecosystem only
- ❌ No deliberation structure

---

## Category 5: Decision Journal / Tracking Tools

### Decision Journal App
- **Website:** https://decisionjournalapp.com/
- **Price:** $4.99/month or $19.99/year
- **Platforms:** iOS, Android

**Alignment:**
- ✅ Tracks decisions with reasoning
- ✅ Reminders to review decisions
- ✅ Outcome tracking
- ✅ Tags and search
- ❌ Personal journaling only
- ❌ No idea relationships or evolution
- ❌ No AI integration

### Yorick
- **Website:** https://www.yorick.xyz/
- **Focus:** Find flaws in reasoning over time

**Key feature:** Tracks relationship between decision quality and outcomes - acknowledges that good decisions can have bad outcomes and vice versa.

### Loqbooq
- **Website:** https://loqbooq.app/
- **Focus:** Team decision logs

**Alignment:**
- ✅ Records what was decided and why
- ✅ Slack integration
- ❌ Team-focused, not personal deliberation

---

## Category 6: Collaborative Decision-Making

### Loomio ⭐ Worth Studying
- **Website:** https://www.loomio.com/
- **Source:** https://github.com/loomio/loomio
- **Price:** From $10/month (self-host for free)
- **Status:** Active, open source (AGPL)

**Alignment:**
- ✅ Deliberation-focused (not just voting)
- ✅ Discussion → Proposal → Decision workflow
- ✅ Decision archive with searchable history
- ✅ Time-bound proposals (prevents stalling)
- ✅ Open source
- ❌ Group-focused, not individual
- ❌ No idea backlog concept
- ❌ Not AI-integrated

**Key insight:** Loomio's workflow (discussion → proposal → decision with timeline) is close to deliberation as process. The time-bounding prevents endless deliberation.

**Worth studying** for workflow design even if target audience (groups) differs from SEEDS (individual).

### ConsiderIt
- **Source:** https://github.com/Considerit/ConsiderIt
- **Status:** Open source (AGPL), academic research tool

**Alignment:**
- ✅ Explicitly designed for personal deliberation
- ✅ Framed around pros/cons
- ✅ Research-backed (affects standpoints, knowledge, understanding)
- ❌ Public deliberation focus
- ❌ Not actively maintained for production use

**Research finding:** ConsiderIt has an "educative design" that teaches users refined communication habits and breaks complex discussions into simpler argument pieces.

---

## Category 7: Argument Mapping Tools

### Rationale (ReasoningLab)
- **Website:** https://www.reasoninglab.com/
- **Price:** 30 EUR/month
- **Focus:** Critical thinking, argument mapping

**Alignment:**
- ✅ Visual argument structure
- ✅ Research-backed (5 years university research)
- ❌ Educational focus
- ❌ Not for personal idea management

### Argunet
- **Website:** http://www.argunet.org/
- **Status:** Open source, 50,000+ downloads
- **Focus:** Graphical argument mapping

**For "visual thinkers" who prefer drawing argument maps.**

### draw.io with AI Smart Templates
- **Website:** https://drawio-app.com/
- **Feature:** AI-assisted argument map generation

Can generate basic argument map structure from prompts. Free, widely used.

---

## Category 8: AI-Assisted Thinking

### Human-AI Deliberation Framework (Academic)
- **Paper:** https://arxiv.org/abs/2403.16812 (CHI 2025)
- **Concept:** LLM-empowered deliberative AI

**Key ideas:**
- Dimension-level opinion elicitation
- Deliberative discussion between human and AI
- Decision updates based on discussion
- Outperforms traditional explainable AI

**Relevance:** Academic framework for exactly what SEEDS envisions - AI as deliberation partner. Not a tool you can use, but informs design.

### The Habermas Machine
- **Publication:** Science, May 2025
- **Finding:** AI can help humans find common ground in deliberation

AI system that outperformed human mediators at reducing intra-group divisions and fostering consensus. Suggests AI-mediated deliberation is promising.

### SequentialThinking MCP Server
- **Integration:** Works with Claude Desktop
- **Function:** Explicit reasoning documentation during conversations

Each reasoning step documented, with revision capabilities. Closer to what SEEDS might want for tracking deliberation within AI conversations.

---

## Category 9: Defunct/Historical (For Reference)

### Athens Research
- **Status:** No longer maintained (pivoted)
- **Was:** Open-source Roam alternative, YC W21

### Foam
- **Source:** https://github.com/foambubble/foam
- **Status:** Active but limited adoption
- **Approach:** VS Code + Markdown + GitHub

For developers who want note-taking in their IDE. Less polished than Obsidian.

---

## Synthesis: What Would SEEDS Need to Be?

Based on this research, SEEDS would need to combine:

| Capability | Best Existing Example |
|------------|----------------------|
| **Idea as first-class entity** | Capacities (objects), Tana (nodes) |
| **Lifecycle states** | Logseq (TODO/LATER/NOW), DRed (amber/green) |
| **Quick capture** | Kinopio, Roam daily notes |
| **Idea relationships** | Kinopio "patch cables", Roam bi-directional links |
| **Q&A structure** | IBIS (Issues → Positions → Arguments), QOC |
| **Backlog/defer** | Logseq backlog pattern, Beads |
| **Text-first/CLI** | Argdown, Beads |
| **AI integration** | Tana AI, Intent.build |
| **Deliberation workflow** | Loomio (discussion → proposal → decision) |
| **Version history** | Intent.build (CRDT), Git |

### The Unique SEEDS Value Proposition

None of these tools:
1. Are designed for **individual deliberation with AI assistance**
2. Treat the **deliberation process itself as the artifact** (not just the outcome)
3. Support **domain-agnostic** idea development (software, RPGs, life decisions)
4. Make it easy to **jot and defer** during mind-racing moments
5. Are built **CLI-first** for developer/agent workflows

---

## Recommendations

### Tools Worth Installing/Trying

1. **Kinopio** - Quick spatial thinking, low friction, patch-cable connections
2. **Logseq** - Closest workflow (TODO/LATER states) among PKM tools
3. **Compendium** - Historical reference for full IBIS implementation
4. **Decision Journal App** - See how decision tracking works in practice
5. **Argdown** (VS Code) - For argument visualization/export

### Concepts Worth Borrowing

1. **From IBIS/QOC:** Issues → Options → Arguments structure
2. **From Loomio:** Time-bounded proposals, decision archive
3. **From DRed:** Status colors (open/resolved), embedded in workflow
4. **From Kinopio:** Connection cables between ideas
5. **From Logseq:** TODO/LATER/NOW lifecycle states
6. **From Intent.build:** Automatic capture, provenance linking
7. **From Beads:** CLI-first, agent-friendly, backlog management

### The SEEDS Differentiator

Build the tool that:
- **Helps ideas grow** (deliberation as nurturing, not just capture)
- **Tracks the journey** (not just the destination)
- **Works with AI** (agent-friendly from day one)
- **Stays out of the way** (quick capture during mind-racing)
- **Produces ADRs** (the fruit from the seed)

---

## Sources

### Deliberation & Argument Mapping
- [Argdown](https://argdown.org/)
- [Kialo](https://www.kialo.com/)
- [Argunet](http://www.argunet.org)
- [Compendium Download](https://cognexus.org/download_compendium.htm)
- [ConsiderIt - GitHub](https://github.com/Considerit/ConsiderIt)
- [Loomio](https://www.loomio.com/)

### PKM / Networked Thought
- [Obsidian](https://obsidian.md/)
- [Roam Research](https://roamresearch.com/)
- [Logseq](https://logseq.com/)
- [Tana](https://tana.inc/)
- [Capacities](https://capacities.io/)
- [Mem AI](https://mem.ai/)

### Visual Thinking
- [Heptabase](https://heptabase.com/)
- [Scrintal](https://scrintal.com/)
- [Kinopio](https://kinopio.club/)
- [Muse](https://museapp.com/)

### Decision Tracking
- [Decision Journal App](https://decisionjournalapp.com/)
- [Yorick](https://www.yorick.xyz/)
- [Loqbooq](https://loqbooq.app/)

### Intent Capture
- [Intent.build](https://intent.build/)

### Academic Research
- [Human-AI Deliberation (CHI 2025)](https://arxiv.org/abs/2403.16812)
- [Habermas Machine (Science 2025)](https://www.science.org/doi/10.1126/science.adq2852)
- [ConsiderIt Research](https://www.researchgate.net/publication/221517927_ConsiderIt_Improving_structured_public_deliberation)

### Tool Comparisons
- [Best PKM Apps 2025](https://toolfinder.co/lists/best-pkm-apps)
- [Second Brain Apps 2025](https://toolfinder.co/lists/best-second-brain-apps)
- [Idea Management Software 2025](https://www.aha.io/blog/idea-management-software-what-are-the-best-tools-for-2025)

---

*Research compiled 2026-01-27 for SEEDS project planning*
