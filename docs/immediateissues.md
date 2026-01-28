# Immediate Issues: ADR Workflow Discovery

**Date:** 2026-01-22
**Context:** Conversation during review of proposed ADRs

---

## The Triggering Question

While walking through 8 proposed ADRs awaiting evaluation, the first one (adr-145: "Define Integration Strategy with Beads") was too vague to evaluate. This raised a meta-question:

> "Where does this feedback get stored? Where do these questions get stored? How do these questions end up getting answered for this ADR?"

## The Discovery Process

### What We Found in ADR Literature

From `docs/what_i_know_about_adr.md`:

1. **ADRs capture outcomes, not journeys**: "ADRs capture the outcome of larger explorations documented in RFCs or design docs. They're summaries, not replacements."

2. **Discussion happens elsewhere**: Traditional ADR practice assumes:
   - A team to have discussions with
   - External venues (meetings, RFCs, design docs) for exploration
   - The ADR author already knows the decision they want to propose

3. **No standard "deferred" status**: Only Proposed → Accepted → Deprecated/Superseded

4. **Immutability is core**: You don't edit accepted ADRs, you supersede them

### The Gap for Solo/AI-Assisted Workflows

For a solo user working with an AI assistant:
- Discussion happens in **ephemeral Claude sessions**
- There's no persistent place to capture "I have questions about this"
- No way to say "defer this, here's why"
- The exploration that leads to a decision has nowhere to live

## Key Realizations

### 1. ADRs Need Supporting Exploration Artifacts

Ryan observed:
> "ADRs could represent large bodies of discussion... ADRs could reference specific lines or capture snippets from those larger conversations. My boss and I transcribe all of our conversations now."

This suggests ADRs should be able to reference:
- Meeting transcripts
- Design documents
- RFC discussions
- Claude conversation exports

### 2. Questions and Answers as First-Class Entities

When reviewing an ADR, questions arise. These need tracking:
- **One ADR → Many Questions**
- **One Question → Many Answers** (different LLMs, human input, different perspectives)
- Questions and answers might be separate entities with their own lifecycle

This led to creating: **adr-665: Add Question-Answer Tracking for ADR Exploration**

### 3. The Tool We Actually Need

Ryan's key insight:
> "I'm actually maybe more interested in developing a tool that its ultimate product is an ADR, but... captures the thinking that went in, the exploration and thinking that went in to the process before the ADR was generated and sort of set in stone."

This is a **different tool** than what ADRB was originally conceived as:

| Original ADRB Concept | Emerging Concept |
|----------------------|------------------|
| Track and manage ADRs | Generate ADRs as final output |
| ADRs as the primary artifact | ADRs as polished summaries |
| Focus on the decision record | Focus on the decision-making process |

### 4. RFCs May Be Part of the Answer

RFCs (Request for Comments) are mentioned in ADR literature as the place where exploration happens before ADRs are written. We need to understand:
- What is the RFC philosophy and structure?
- What tools exist for RFC management?
- Do we need RFC tracking as part of this tooling?

This led to creating: **adrb-s5i: Research RFCs: philosophy, structure, tools, ecosystem**

### 5. Where Does This Conversation Live?

This very conversation demonstrates the problem. We're having a discovery discussion that:
- Contains valuable insights about tool design
- Would be lost when the Claude session ends
- Needs to inform future development

Capturing it in this markdown file is a stopgap, but raises the question: **what tool/structure should capture this kind of exploration?**

## Claude's Feedback

The user's realization represents a significant pivot in thinking about ADRB. Some observations:

1. **The problem is real**: ADR tooling assumes you already know what you want to decide. There's a gap for the "figuring it out" phase.

2. **Beads might partially address this**: Work items in Beads can capture "explore X" or "research Y" tasks, but they don't have a structure for Q&A or discussion threads.

3. **The Q&A structure is interesting**: Having questions that can receive multiple answers from different sources (LLMs, humans) creates a kind of "deliberation record" that could be valuable.

4. **Risk of scope creep**: The original ADRB was meant to be a simple ADR tracker. Expanding to "exploration + decision support tool" is a much bigger scope. Worth being intentional about whether that's the goal.

5. **Transcripts as source material**: The mention of transcribing conversations suggests a workflow where:
   - Raw conversations happen (human-human, human-AI)
   - They get transcribed/captured
   - Insights get extracted into structured artifacts (questions, answers, eventually ADRs)

## Open Questions

1. Should exploration artifacts (questions, discussion, research) live in ADRB, Beads, or a new tool?

2. What's the relationship between:
   - Meeting transcripts
   - RFCs
   - Design docs
   - Questions/Answers
   - ADRs

3. Is "proposed" the right initial status for ADRs, or do we need "draft" or "exploring"?

4. How do we prevent the exploration tool from becoming a documentation graveyard?

## Actions Taken

1. **Created bead adrb-s5i**: Research RFCs to understand if we need RFC tracking
2. **Created ADR adr-665**: Proposal to add Q&A tracking for ADR exploration
3. **Created this document**: Capturing the conversation and insights

## What's Still Unresolved

- The 8 proposed ADRs still need evaluation
- ADR adr-145 (Beads integration) should probably be deferred until we have more clarity
- The fundamental question of "what tool are we building" needs an answer

---

*This document itself is an example of the problem: valuable exploration captured in an ad-hoc markdown file because there's no better place for it.*
