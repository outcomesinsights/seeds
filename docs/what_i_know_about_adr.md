# What I Know About Architecture Decision Records (ADR)

## Table of Contents

1. [History and Origin](#history-and-origin)
2. [Philosophy and Purpose](#philosophy-and-purpose)
3. [Core Concepts and Definitions](#core-concepts-and-definitions)
4. [The Original Nygard Format](#the-original-nygard-format)
5. [Templates and Formats](#templates-and-formats)
6. [Tools and Ecosystem](#tools-and-ecosystem)
7. [Best Practices](#best-practices)
8. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
9. [When to Write an ADR](#when-to-write-an-adr)
10. [When NOT to Write an ADR](#when-not-to-write-an-adr)
11. [Real-World Examples and Adoption](#real-world-examples-and-adoption)
12. [Integrations and Related Practices](#integrations-and-related-practices)
13. [Sources and Further Reading](#sources-and-further-reading)

---

## History and Origin

### The Birth of ADRs (2011)

Architecture Decision Records were popularized by **Michael Nygard** in his November 2011 blog post ["Documenting Architecture Decisions"](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) on the Cognitect blog.

At the time, Nygard's team had been using the format on projects since early August 2011. Despite the short trial period, feedback from both clients and developers was positive. Developers who rotated through ADR-using projects appreciated the context they received by reading the records.

Nygard identified a critical problem: when teams don't document decisions, future developers either:
- **Blindly accept** past choices without understanding them (risking paralysis when context shifts)
- **Blindly change** them (potentially undermining non-functional requirements the original decision satisfied)

### Industry Adoption

Seven years after Nygard's article, **ThoughtWorks** placed Lightweight Architecture Decision Records in the **"Adopt"** category of their Technology Radar (2018)—their strongest endorsement, indicating the industry should actively use this technique.

The history of architecture decision recording actually extends back to the late 1990s, but Nygard's lightweight, practical format crystallized the practice into something widely adoptable.

---

## Philosophy and Purpose

### The Core Problem: Knowledge Loss

> "Often enough, the why and how of the feature are kept in the decision-making developer's brain. Newcomers to the project then are left to wonder why certain things are done in a certain way."

Most teams make decisions verbally during meetings, and those decisions are eventually lost or forgotten—leaving only the current state of things without the reasoning behind them.

### Developer Empathy

> "If your software survives you, someone else will be holding their nose at it... We need more developer to developer empathy."

ADRs are an act of empathy toward future developers (including your future self). They preserve decision-making context for posterity.

### Key Philosophical Principles

1. **Decisions are first-class artifacts**: Architectural decisions deserve the same attention as code and tests.

2. **Context matters as much as the decision**: Understanding *why* is often more valuable than knowing *what* was decided.

3. **Immutability preserves history**: ADRs should be immutable once accepted. Don't alter them—supersede them with new ADRs.

4. **Small documents have a better chance**: "Large documents are never kept up to date. Small, modular documents have at least a chance at being updated." — Michael Nygard

5. **Conversations over commands**: Architecture need not be top-down from centralized architects. ADRs enable decentralized decision-making through the Advice Process.

### The Cost of Undocumented Decisions

- Duplicated efforts (engineers solve the same problems repeatedly)
- Competing solutions (multiple libraries doing the same thing)
- Lost productivity during ownership transfers
- Compound problems requiring large migrations later

---

## Core Concepts and Definitions

### Architectural Decision (AD)
A justified design choice that addresses a functional or non-functional requirement that is **architecturally significant**.

Martin Fowler's definition: "Software architecture is those decisions which are both important and hard to change."

### Architecturally Significant Requirement (ASR)
A requirement that has a **measurable effect** on the architecture and quality of a software/hardware system.

### Architecture Decision Record (ADR)
A short text document that captures a **single** architectural decision along with its context and consequences.

### Architecture Decision Log (ADL)
The collection of all ADRs maintained throughout a project—forming a decision history.

### Architectural Knowledge Management (AKM)
The broader discipline encompassing ADR practices for capturing and sharing architectural knowledge.

---

## The Original Nygard Format

Michael Nygard proposed a simple, pattern-like format with five sections:

```markdown
# Title

## Status
[Proposed | Accepted | Deprecated | Superseded]

## Context
[Describe the forces at play, including technological, political, social,
and project organizational. These forces are likely in tension.]

## Decision
[State the decision in active voice: "We will..."]

## Consequences
[What results from applying the decision. All consequences should be listed,
not just the "positive" ones.]
```

### Key Characteristics

- **Title**: Short noun phrases identifying the decision (e.g., "ADR 9: LDAP for Multitenant Integration")
- **Context**: Value-neutral description of forces at play—factual, not argumentative
- **Decision**: Active voice statement beginning "We will..."
- **Status**: Proposed → Accepted → (later) Deprecated or Superseded
- **Consequences**: ALL impacts—positive, negative, and neutral

ADRs should be:
- **1-2 pages long** at most
- Written as **conversations with future developers**
- Using **complete sentences** rather than bullet fragments
- Stored in **version control**, alongside the code

---

## Templates and Formats

### 1. Michael Nygard (Original)
The simple five-section format described above. Most widely used.

### 2. MADR (Markdown Architectural Decision Records)
[MADR](https://adr.github.io/madr/) - More structured with explicit options analysis.

**Current version**: MADR 4.0.0 (September 2024)

**Core Sections**:
- Context and Problem Statement
- Decision Drivers (optional)
- Considered Options
- Decision Outcome
- Consequences (positive/negative combined)
- Pros and Cons of Options (optional)
- More Information (optional)

**File naming**: `NNNN-title-with-dashes.md` (e.g., `0001-use-postgresql-for-database.md`)

The name MADR is pronounced "matter" [ˈmæɾɚ]—as in "decisions that matter."

### 3. Y-Statements
A single-sentence format for capturing decisions concisely:

**Short form**:
> "In the context of `<use case>`, facing `<concern>` we decided for `<option>` to achieve `<quality>`, accepting `<downside>`."

**Long form**:
> "In the context of `<use case>`, facing `<concern>`, we decided for `<option>` and neglected `<other options>`, to achieve `<qualities>`, accepting `<downsides>`, because `<rationale>`."

**Example**:
> "In the context of the Web shop service, facing the need to keep user session data consistent across instances, we decided for the Database Session State Pattern (and against Client Session State or Server Session State) to achieve cloud elasticity, accepting that a session database needs to be designed, implemented, and replicated."

Originated from Olaf Zimmermann at SATURN 2012, visualized as the letter "Y" (pronounced like "why").

### 4. Jeff Tyree and Art Akerman Format
More sophisticated template with additional sections for assumptions, constraints, and related decisions.

### 5. Business Case Template
MBA-oriented with cost/benefit analysis and SWOT.

### 6. arc42 Integration
Comprehensive architecture documentation with ADRs in Section 9.

### Template Comparison

| Template | Complexity | Best For |
|----------|------------|----------|
| Nygard | Simple | Most teams, quick adoption |
| MADR | Moderate | Teams wanting explicit options analysis |
| Y-Statement | Minimal | Quick captures, inline documentation |
| Tyree/Akerman | Comprehensive | Enterprise contexts with many stakeholders |
| Business Case | Complex | Decisions requiring business justification |

---

## Tools and Ecosystem

### Command-Line Tools

#### adr-tools (Original - Bash)
[npryce/adr-tools](https://github.com/npryce/adr-tools) - The original CLI tool.

```bash
# Install (macOS/Linux)
brew install adr-tools

# Initialize ADR directory
adr init doc/architecture/decisions

# Create new ADR
adr new Implement as Unix shell scripts

# Create ADR that supersedes another
adr new -s 9 Use Rust for performance-critical functionality

# Get help
adr help
```

#### Python Alternatives
- **[adr-tools-python](https://pypi.org/project/adr-tools-python/)**: `pip3 install adr-tools-python`
- **[ADR-py](https://github.com/AlTosterino/ADR-py)**: Modern Python 3.11+ rewrite
- **[pyadr](https://github.com/flepied/madr-tools-python)**: MADR-focused with lifecycle management
- **adr-viewer**: Generates websites from ADR collections

#### Go Alternatives
- **[marouni/adr](https://github.com/marouni/adr)**: `go install github.com/marouni/adr`
- **[abebars/adr](https://github.com/abebars/adr)**: Similar Go implementation

#### Other Languages
- **dotnet-adr**: Cross-platform .NET Global Tool
- **Talo**: CLI for ADRs, RFCs, and custom design documents
- **Rust-based tools**: Various implementations available

### Web/GUI Tools

#### Log4brains
[thomvaill/log4brains](https://github.com/thomvaill/log4brains) - Docs-as-code knowledge base.

Features:
- Preview ADRs locally with hot reload
- Publish as static website (GitHub Pages, GitLab Pages, S3)
- Uses MADR format by default
- Includes features of most other tools combined

#### ADR Manager (Web)
Web application connecting to GitHub repositories to render ADRs.

#### ADR Manager (VS Code Extension)
Visual Studio Code plugin with two modes (basic/professional) organized by template sections.

### Platform Integrations

#### Backstage ADR Plugin
[@backstage-community/plugin-adr](https://www.npmjs.com/package/@backstage-community/plugin-adr)

- Explores ADRs associated with entities
- Search ADRs across the entire organization
- Supports MADR 2.x and 3.x templates
- Configure via `backstage.io/adr-location` in catalog-info.yaml

#### Structurizr
C4 model visualization and documentation platform with ADR support.

#### docToolchain
Docs-as-code implementation for software architecture documentation.

### Supporting Tools

- **adr-log**: Generates `index.md` from ADR collections
- **ArchUnit**: Architecture unit testing (validates decisions are followed)

---

## Best Practices

### Content and Structure

1. **Focus on a single decision**: Keep ADRs concise. Don't hesitate to split decisions if necessary.

2. **Separate design from decision**: Use separate design documents to explore alternatives. Reference them in the ADR.

3. **Document the "why," not the "how"**: Implementation details belong elsewhere.

4. **Be specific about context**: Include organizational situation, business priorities, team composition, and skills.

5. **List ALL consequences**: Document positive, negative, AND neutral outcomes. Don't hide downsides.

6. **Use consistent templates**: Pick one template and stick with it across the project.

### Process and Workflow

1. **Store ADRs near the code**: In version control, in the relevant repository, not in wikis or external tools.

2. **Use meaningful file names**: Present-tense imperative phrases: `choose-database.md`, `format-timestamps.md`

3. **Number ADRs sequentially**: `0001-record-architecture-decisions.md`, `0002-use-postgresql.md`

4. **Keep meetings short**: 30-45 minutes maximum. Use "readout" style where participants read the ADR for 10-15 minutes before discussing.

5. **Push for timely decisions**: 1-3 ADR readouts should be sufficient. More sessions indicate scope problems.

6. **Review and approve as a team**: ADR approval is a team effort, not a single person's decision.

7. **Embrace immutability**: Don't change accepted ADRs. Supersede them with new ADRs.

### Organizational Practices

1. **All developers should contribute**: Not just senior architects. Implement peer review.

2. **Regular ADR sessions**: In active projects, hold regular ADR discussion and review meetings.

3. **Use the Advice Process**: Anyone can make an architectural decision, but must consult those affected and subject matter experts.

4. **Integrate with code review**: Validators check changes against relevant ADRs during peer review.

5. **Periodic reviews**: Review ADRs annually to identify those needing updates or supersession.

---

## Anti-Patterns to Avoid

### ADR Creation Anti-Patterns

| Anti-Pattern | Description |
|--------------|-------------|
| **Blueprint/Policy in Disguise** | Writing style is cookbook-like or commanding, not journal-style |
| **Mega-ADR** | Multiple pages stuffed with detailed architecture specs, diagrams, code |
| **Novel/Epic** | Entire Software Architecture Document squeezed into one ADR |
| **Fairy Tale** | Only pros listed, no cons; shallow "wishful thinking" justification |
| **Sales Pitch** | Marketing language, exaggerations without evidence |
| **Free Lunch Coupon** | Ignoring difficult or long-term consequences |
| **Sprint/Rush** | Only one option considered; only short-term effects discussed |
| **Tunnel Vision** | Isolated context; ignoring operations/maintenance perspectives |
| **Dummy Alternative** | Presenting non-viable options to favor the preferred solution |
| **Maze** | Topic doesn't match content; discussions derail |
| **Magic Tricks** | False urgency, pseudo-accuracy with weighted scoring |

### ADR Review Anti-Patterns

| Anti-Pattern | Description |
|--------------|-------------|
| **Pass Through** | Minimal/shallow comments; document only skimmed |
| **Copy Edit** | Focuses solely on grammar, not content |
| **Siding/Dead End** | Topic switches unexpectedly; stops without advice |
| **Self Promotion** | Recommends reviewer's own work; conflict of interest |
| **Power Game** | Relies on hierarchy instead of technical arguments |
| **Offended Reaction** | Defensively protects criticized positions |
| **Groundhog Day** | Repetitive messaging without progression |

### Decision-Making Anti-Patterns

1. **No decision made**: Fear of making the wrong choice leads to paralysis
2. **Decision without justification**: Same topic gets discussed repeatedly
3. **Decision not captured**: Team members forget or don't know a decision was made

---

## When to Write an ADR

Write an ADR when the decision involves:

- **Structure**: Patterns like microservices, monolith, event-driven
- **Non-functional requirements**: Security, high availability, fault tolerance, performance
- **Dependencies**: Component coupling, third-party integrations
- **Interfaces**: APIs, published contracts, integration points
- **Construction techniques**: Languages, libraries, frameworks, tools, processes

### The Spotify Guidance

Write ADRs in three scenarios:

1. **Backfilling undocumented decisions**: If a "blessed solution" exists but isn't documented, capture it.
2. **After large changes**: When RFCs conclude, document the final decision.
3. **For small decisions**: Even minor choices deserve documentation to prevent compounding problems.

> "An ADR should be written whenever a decision of significant impact is made; it is up to each team to align on what defines a significant impact."

### Architecturally Significant Decisions

Michael Nygard defines architecturally significant decisions as those that impact:
- Structure
- Non-functional characteristics
- Dependencies
- Interfaces
- Construction techniques

---

## When NOT to Write an ADR

Skip ADRs for:

- **Tiny/minimal-risk decisions**: Self-contained, single-developer choices
- **Decisions already covered**: By existing standards, policies, or documentation
- **Temporary decisions**: Workarounds, POCs, spikes
- **Day-to-day small decisions**: Little to no lasting impact
- **Limited scope**: Doesn't affect team beyond immediate context

> "Teams should create an ADR when they want future developers to understand the 'why' of what they're doing."

If no one will ever wonder "why did we do this?", you probably don't need an ADR.

---

## Real-World Examples and Adoption

### Open Source Projects Using ADRs

- **Backstage** (Spotify): Uses MADR format with their own [ADR documentation](https://backstage.io/docs/architecture-decisions/)
- **GOV.UK**: Multiple UK government services including GOV.UK Publishing Components, Data.gov.uk, and GOV.UK Docker
- **Open Data Hub**: Collection of ADRs for the AI/ML platform
- **Various AWS projects**: ParallelCluster UI, VMware Secrets Manager

### Enterprise Adoption

#### UK Government
The Government Digital Service (GDS) released an official [ADR Framework](https://www.gov.uk/government/publications/architectural-decision-record-framework/architectural-decision-record-framework) (December 2025) for use across the UK public sector, with four escalation levels:
- Team/Working Group (single team impact)
- Cross-team/Programme (multiple teams)
- Department-wide (new standards/precedents)
- Cross-government (national strategy alignment)

#### AWS
AWS Prescriptive Guidance provides extensive ADR documentation and has written 200+ ADRs internally. Their guidance emphasizes:
- Immutability once accepted
- Clear ownership
- Integration with code review
- Decision log maintenance

#### Microsoft Azure
Azure Well-Architected Framework includes ADR guidance as part of the architect role.

### Adoption Statistics

According to an IEEE MSR study on GitHub:
- ADR adoption is still relatively low but increasing yearly
- ~50% of repositories with ADRs contain just 1-5 ADRs (tried but not fully adopted)
- Nygard's template is most commonly used

---

## Integrations and Related Practices

### arc42
ADRs fit naturally into **Section 9** of arc42 architecture documentation. arc42 recommends using ADRs for every important decision, presented as a list ordered by importance or in detailed form.

### C4 Model
ADRs complement C4 diagrams by documenting the "why" behind structural decisions shown in context, container, and component diagrams.

### Technology Radar
An internally-customized mapping of technology adoption can reference ADRs as evidence for adoption decisions.

### Architecture Advisory Forum
Weekly meetings where teams present proposed decisions (via ADRs) and receive advice without giving up decision ownership.

### Team-Sourced Principles
8-15 SMART principles that guide decisions. ADRs reference which principles influenced choices.

### RFCs and Design Documents
ADRs capture the *outcome* of larger explorations documented in RFCs or design docs. They're summaries, not replacements.

---

## Sources and Further Reading

### Foundational Resources

- [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) - Michael Nygard's original 2011 blog post
- [ADR GitHub Organization](https://adr.github.io/) - Central hub for ADR resources
- [joelparkerhenderson/architecture-decision-record](https://github.com/joelparkerhenderson/architecture-decision-record) - Comprehensive examples and templates

### Templates

- [MADR (Markdown ADR)](https://adr.github.io/madr/) - Structured format with options analysis
- [ADR Templates](https://adr.github.io/adr-templates/) - Collection of various templates
- [Y-Statements](https://socadk.github.io/design-practice-repository/artifact-templates/DPR-ArchitecturalDecisionRecordYForm.html) - Single-sentence format

### Tools

- [adr-tools](https://github.com/npryce/adr-tools) - Original CLI by Nat Pryce
- [Log4brains](https://github.com/thomvaill/log4brains) - Docs-as-code knowledge base
- [Decision Capturing Tools](https://adr.github.io/adr-tooling/) - Comprehensive tool list

### Enterprise Guidance

- [AWS ADR Process](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html)
- [Azure Well-Architected Framework ADR](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)
- [UK Government ADR Framework](https://www.gov.uk/government/publications/architectural-decision-record-framework/architectural-decision-record-framework)
- [GDS Way: Architecture Decisions](https://gds-way.digital.cabinet-office.gov.uk/standards/architecture-decisions.html)

### Best Practices Articles

- [ThoughtWorks Technology Radar: Lightweight ADRs](https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records)
- [How to Create ADRs — and How Not To](https://www.ozimmer.ch/practices/2023/04/03/ADRCreation.html) - Olaf Zimmermann
- [How to Review ADRs — and How Not To](https://ozimmer.ch/practices/2023/04/05/ADRReview.html) - Olaf Zimmermann
- [When Should I Write an ADR](https://engineering.atspotify.com/2020/04/when-should-i-write-an-architecture-decision-record) - Spotify Engineering
- [Scaling Architecture Conversationally](https://martinfowler.com/articles/scaling-architecture-conversationally.html) - Andrew Harmel-Law on martinfowler.com

### Books

- *Fundamentals of Software Architecture* - Mark Richards & Neal Ford
- *Building Evolutionary Architectures* - Neal Ford, Rebecca Parsons, Patrick Kua
- *arc42 FAQ* - Gernot Starke & Peter Hruschka

### Research

- [Markdown Architectural Decision Records: Format and Tool Support](https://ceur-ws.org/Vol-2072/paper9.pdf) - Academic paper on MADR
- [Using Architecture Decision Records in Open Source Projects](https://ieeexplore.ieee.org/document/10155430/) - IEEE MSR study on GitHub ADR adoption

---

## Quick Reference: Starting with ADRs

### Minimal Setup

```bash
# Create directory
mkdir -p docs/decisions

# Create first ADR (meta-decision to use ADRs)
cat > docs/decisions/0001-record-architecture-decisions.md << 'EOF'
# 1. Record Architecture Decisions

## Status
Accepted

## Context
We need to record the architectural decisions made on this project.

## Decision
We will use Architecture Decision Records, as described by Michael Nygard.

## Consequences
See Michael Nygard's article, linked above.
EOF
```

### With adr-tools

```bash
brew install adr-tools
adr init docs/decisions
adr new Use PostgreSQL for primary database
```

### Key Files

```
project/
├── docs/
│   └── decisions/
│       ├── 0001-record-architecture-decisions.md
│       ├── 0002-use-postgresql-for-database.md
│       ├── 0003-adopt-microservices-architecture.md
│       └── index.md (optional, generated by adr-log)
└── ...
```

### ADR Review Checklist

1. Is the problem significant enough for an ADR?
2. Can the options solve the identified problem?
3. Are decision criteria mutually exclusive and comprehensive?
4. If criteria conflict, are priorities established?
5. Does the chosen solution work with sound rationale?
6. Are consequences reported objectively (including negatives)?
7. Is the solution actionable with clear next steps?

---

*Document compiled from research across 40+ sources including the original Michael Nygard article, ThoughtWorks Technology Radar, AWS Prescriptive Guidance, UK Government frameworks, Spotify Engineering, and various community blog posts.*
