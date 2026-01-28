# SEEDS Specification - First Pass

> Captured from design conversations (2026-01-25/26 and 2026-01-27)

## Core Vision

**"I don't want to spend time/energy/thinking on _managing_ seeds, such as fiddling with states, calling out relationships, shuffling around ideas. I want the tool to work for me, not me work for the tool."**

The tool should feel effortless for both humans and AI agents. Natural language interaction is the goal:
- "What is related to this seed?"
- "I think this is a constraint for XYZ"
- "I think we've answered this question with ABC's answer, specifically the part that says '...'"
- "Look at this conversation and create new seeds"

---

## Core Model

### Everything is a Seed

Seeds are the fundamental unit. Deliberation is the activity of working through seeds, not a separate entity or container.

### Seeds are Polymorphic

A seed can be:
- **Statement**: An assertion, proposal, or decision (e.g., "use SQLite")
- **Topic**: A subject requiring deliberation (e.g., "storage approach", "what language?")
- **Question**: Something needing an answer (e.g., "how do we handle concurrent writes?")

The type affects how resolution works, but the underlying entity is always a seed.

### Options/Proposals

When deliberating a topic, options are proposed as seeds related to that topic:
- Topic: "what language?"
  - Option: "use Python" (with context: "AI proposed as fastest for MVP")
  - Option: "use Go" (with context: "not my strongest language, but Beads uses it")

Options appear to be statements with a specific relationship to a topic ("proposed for", "option for", "candidate for" - exact relationship TBD).

---

## Seed States

### Active States
- **Open**: Under active consideration
- **Backlogged**: Captured but not currently being worked

### Terminal States
- **Accepted**: Adopted, confirmed, we're doing this
- **Rejected**: Explicitly not doing this
- **Abandoned**: Set aside, not actively rejected but not pursued
- **Superseded**: Replaced by another seed

All seeds ultimately reach a terminal state.

### State Behavior
- Rejected/abandoned seeds are preserved for reference
- They surface when exploring relationships but not in active reviews
- You never know when you might need to revisit an abandoned or rejected idea

---

## Relationships

### Nesting/Dependencies
- Seeds can be nested under other seeds
- A parent seed cannot be resolved until its nested children are resolved
- Example: "storage approach" topic cannot resolve until "use SQLite" (an option) reaches a terminal state

### Relationship Discovery
Relationships can be established:
1. **At creation time**: "In relation to storage approach, use SQLite"
2. **During review**: AI suggests connections when reviewing seeds
3. **On demand**: User asks "what is related to this seed?"

### Explicit vs Possible Relationships
User envisions distinguishing between:
- **Explicitly related**: User or AI has confirmed the relationship
- **Possibly related**: AI suggests a potential connection

This distinction could be a helpful signal to both humans and AI.

### Relationship Permanence
- Declaring seeds as unrelated doesn't make them "standalone forever"
- A new seed introduced later might create a relationship
- No seed is ever truly declared permanently standalone

---

## Questions and Answers

### Multiple Answerers
More than one participant can answer a question:
- AI can research and provide an answer
- Human can provide an answer
- Multiple answers might exist

### Closure
- Questions need to be **explicitly stated as answered**
- Closure includes attribution (who/what answered it)
- May include a summary of which answers resolved the question
- Both AI and humans can propose closure

---

## Constraints and Inputs

When deliberating, various inputs inform decisions:
- **Constraints**: "SQLite doesn't support concurrent writes"
- **Inputs/Preferences**: "Whichever language is best for AI is fine with me"
- **Context**: "Go is the language Beads was written in"

**Open question**: Are these seeds in their own right, or metadata/notes attached to seeds? User is uncertain: "I don't know if they are individual seed types, or just things recorded in seeds directly or associated with seeds but are somehow not exactly seeds."

---

## Source Materials (Transcripts, Documents)

### Transcripts are NOT Seeds
They are source material from which seeds are derived. Seeds reference back to specific lines in source documents.

### Storage
Source materials should be stored in the tool alongside seeds, but as a separate entity type.

### Processing Workflow
When feeding in a transcript/document:
1. Store it as source material
2. Extract potential seeds from the document
3. Find existing seeds that match and merge transcript references into them (possibly tweaking with new information)
4. Create new seeds for unmatched extractions
5. Re-explore relationships when seeds are significantly changed or brand new

### Repeatable Extraction
The act of turning a transcript into seeds can be repeated multiple times. The current state of the seeds database informs what seeds to parse and propose - it's not a one-time operation.

---

## Workflow Patterns

### Inbox Pattern
Capture fast, refine later. Get the idea into the system as quickly as possible. Revisit later to:
- Tag and refine
- Establish relationships
- Put in right categories
- Achieve "inbox zero"

### Review Process
From the ADR tool experience:
1. Ask for a list of undecided/open items
2. First item surfaces with questions
3. Some questions are relevant now, others go to backlog
4. Process involves: asking questions, finding answers, brainstorming alternatives, listing constraints, exploring the topic space

### Deliberation Complete When
(Naively) when:
- All questions have been answered
- Constraints have been listed
- Proposed approaches have been evaluated (why adopted or not)

---

## AI Role

### Participant vs Facilitator
AI can:
- Research and answer questions
- Propose relationships between seeds
- Suggest closure for questions
- Extract seeds from transcripts
- Propose that seeds might belong to a topic

**Open question**: Is AI a participant in deliberation (contributes seeds, makes decisions) or a facilitator (organizes, prompts, suggests but doesn't decide)?

From the "what language" example: "AI had made a decision. Decision was made." - AI appears to be a legitimate decision-maker in some contexts.

---

## Open Questions

### Seed Structure
1. Are options a distinct seed type, or statements with a "proposed for [topic]" relationship?
2. What is the exact relationship between an option and its topic? ("associated", "proposed for", "candidate for"?)
3. When a topic resolves by accepting one option, are other options automatically rejected? Or do they need explicit rejection?

### Constraints/Inputs
4. Are constraints seeds in their own right, or metadata attached to other seeds?
5. Same question for inputs, evidence, context notes

### Relationships
6. What relationship types do we need? (parent/child, option-for, constraint-on, related-to, answers, supersedes, etc.)

### AI Role
7. When does AI have authority to make decisions vs only propose?
8. How is AI attribution captured differently from human attribution?

### Resolution Mechanics
9. Does accepting an option automatically reject alternatives?
10. What does resolution look like for different seed types (topic vs question vs statement)?

---

## Example: "What Language?" Deliberation

```
Topic: "what language?"
├── Option: "use Python"
│   └── Context: "AI proposed as fastest for MVP"
├── Option: "use Go"
│   └── Context: "not my strongest language, but Beads uses it"
├── Input: "whichever is best for AI is fine with me"
└── Resolution: Python ACCEPTED, Go REJECTED
    └── Topic reaches terminal state: RESOLVED
```

This example shows:
- Topic with multiple options
- Options have context/rationale
- User input informed but wasn't an option itself
- Accepting one option resolved the topic
- The fate of rejected options (rejected? abandoned? superseded?)
