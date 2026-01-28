# What I Know About Requests for Comments (RFC)

## Table of Contents

1. [History and Origin](#history-and-origin)
2. [Philosophy and Purpose](#philosophy-and-purpose)
3. [Core Concepts and Definitions](#core-concepts-and-definitions)
4. [The IETF RFC Process](#the-ietf-rfc-process)
5. [Internal/Corporate RFC Processes](#internalcorporate-rfc-processes)
6. [RFC Templates and Formats](#rfc-templates-and-formats)
7. [RFC Lifecycle and Workflow](#rfc-lifecycle-and-workflow)
8. [Tools and Ecosystem](#tools-and-ecosystem)
9. [Best Practices](#best-practices)
10. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
11. [When to Write an RFC](#when-to-write-an-rfc)
12. [When NOT to Write an RFC](#when-not-to-write-an-rfc)
13. [RFCs vs ADRs vs Design Documents](#rfcs-vs-adrs-vs-design-documents)
14. [Real-World Examples and Adoption](#real-world-examples-and-adoption)
15. [Sources and Further Reading](#sources-and-further-reading)

---

## History and Origin

### The Birth of RFCs (April 7, 1969)

The Request for Comments system was invented by **Steve Crocker** in 1969 to help record unofficial notes on the development of ARPANET. On April 7, 1969, Crocker, a graduate student at UCLA, published the first RFC entitled "Host Software" (RFC 1).

RFC 1 defined the design of the host software for communication between ARPANET nodes. This host software would run on Interface Message Processors (IMPs), the precursors to modern Internet routers. The "host software" defined in RFC 1 would later become known as the Network Control Protocol (NCP), the forerunner to modern TCP/IP.

### The Deliberate Choice of Name

The name "Request for Comments" was deliberately chosen to be informal and inviting. Crocker and his colleagues were concerned that formally documenting their concepts might seem like they were taking authority over the network's design. By titling documents "Request for Comments," they made clear these were not official publications and they were asking others to add their input.

In later years, Crocker referred to RFC 1 as "a modest and entirely forgettable memo"—but it established the collaborative, open process that would shape how the ARPANET, and later the Internet, would develop through open discussion, criticism, and iterative refinement.

### The Network Working Group

Steve Crocker formed the "Network Working Group" in 1969. Working with Jon Postel and others, he initiated and managed the RFC process, which is still used today for proposing and distributing contributions. The authors of the first RFCs typewrote their work and circulated hard copies among ARPA researchers. By December 1969, researchers began distributing new RFCs via the newly operational ARPANET.

### Evolution to Standards

RFCs began as informal notes on ARPANET, the precursor to the Internet. Over time, they evolved into formal standards-track documents within the IETF. RFCs have since become official documents of Internet specifications, communications protocols, procedures, and events.

Today, there are over 8,500 RFCs whose publication is managed through a formal process by the RFC Editor team. The RFC series predates the IETF itself.

---

## Philosophy and Purpose

### The Core Principle: Collaborative Development

The RFC process embodies a fundamental belief: the best technical decisions emerge from open discussion and diverse perspectives. Rather than top-down mandates, RFCs invite participation and feedback before decisions are finalized.

> "Request for Comments" clearly states that the main goal is collecting feedback.

### Feedback Before Commitment

Unlike documents that announce decisions already made, RFCs are explicitly designed to gather input *before* committing to a course of action. This distinction is crucial:

- **RFCs** invite criticism and alternatives early
- **Announcements** inform people of decisions after the fact
- **Documentation** records what was done

### Reducing Risk Through Review

By exposing plans to those internal and external to a team, RFCs:

- Minimize risk through early identification of issues
- Create lasting records of technical discussions
- Make reaching agreements asynchronous
- Enable participation from diverse perspectives and expertise

### Accountability Through Writing

Writing and sharing that writing creates accountability. It also almost always leads to more thorough decisions. The act of articulating a proposal in writing forces the author to think through details they might otherwise skip in verbal discussions.

### Building Institutional Knowledge

The RFC process creates a searchable, referenceable history of technical decisions and the discussions that shaped them. This proves invaluable for:

- Onboarding new team members
- Understanding why past decisions were made
- Avoiding repeated discussions of the same topics
- Preserving context across team transitions

---

## Core Concepts and Definitions

### Request for Comments (RFC)

An RFC is a structured proposal for a change, inviting feedback before making a decision. RFCs are written proposals that seek feedback and encourage discussion about technical decisions, their tradeoffs, and implications.

### Design Document

A detailed technical specification that describes how something will be built. Design documents can vary widely in formality and are often used interchangeably with "RFC" at many companies, though some organizations distinguish between the two.

### Internet-Draft (I-D)

In the IETF context, an Internet-Draft is a working document within the standardization process. I-Ds have no formal status, can be changed or dropped by their originators at any time, and have a six-month lifespan. All RFCs start as Internet-Drafts, though many I-Ds never become RFCs.

### Approvers/Stakeholders

Key individuals who must review and sign off on an RFC before it can be considered approved. Complex proposals often have explicit "approver" fields to ensure the right people have reviewed the proposal.

### Comment Period

The time window during which feedback is solicited on an RFC. This period should have limits so proposals don't linger forever. RFCs are meant to drive decision-making, not halt it.

### NABC Framework

A value proposition format sometimes used in RFCs:
- **N**eed: What problem are we solving?
- **A**pproach: How will we solve it?
- **B**enefits: What do we gain?
- **C**ompetition: What are the alternatives?

This format was introduced to SoundCloud by Gavin Bell and has been adopted by Phil Calcado in his structured RFC process.

---

## The IETF RFC Process

### Overview

A Request for Comments (RFC) is a publication in a series from the principal technical development and standards-setting bodies for the Internet, most prominently the Internet Engineering Task Force (IETF). The IETF publishes its technical documentation as RFCs, describing the Internet's technical foundations such as addressing, routing, and transport technologies.

### RFC Streams

There are five streams of RFCs:
1. **IETF**: Standards-track and Best Current Practices
2. **IRTF**: Internet Research Task Force documents
3. **IAB**: Internet Architecture Board documents
4. **Independent Submission**: Non-standards track documents
5. **Editorial**: Editorial and process documents

Only the IETF creates BCPs and RFCs on the standards track.

### Standards Track Maturity Levels

Originally, the standards track had three maturity levels (as defined in RFC 2026):
1. Proposed Standard
2. Draft Standard
3. Standard

In October 2011, RFC 6410 simplified this to two levels:

1. **Proposed Standard**: The initial standards-track RFC status. Many Proposed Standards are actually deployed extensively and represent stable protocols.

2. **Internet Standard**: The highest maturity level, achieved when implementation and operational experience requirements are met. This is relatively rare—most popular IETF protocols remain at Proposed Standard.

### Non-Standards Track Categories

- **Informational**: Documents providing information to the Internet community
- **Experimental**: Documents describing experimental protocols or systems
- **Best Current Practice (BCP)**: Documents describing IETF processes or operational guidelines
- **Historic**: Specifications that have been superseded or are considered obsolete

### Immutability

Once assigned a number and published, an RFC is never rescinded or modified. If amendments are needed, authors publish a revised document. Superseded RFCs are said to be deprecated or obsolete.

---

## Internal/Corporate RFC Processes

### The Adoption of RFCs in Tech Companies

Many Big Tech companies and high-growth startups have adopted RFC-like processes for internal technical decision-making. The process resembles the IETF RFC system but is adapted for corporate contexts.

### Companies Using RFCs/Design Docs

| Company | Name | Notes |
|---------|------|-------|
| **Uber** | RFC | Started early, scaled from tens to thousands of engineers |
| **Google** | Design Docs | Comprehensive design document culture |
| **Spotify** | RFCs and ADRs | "Deeply embedded part of the culture" |
| **Airbnb** | Specs and Design Docs | For both Product and Engineering |
| **LinkedIn** | RFCs | "Strong culture of writing RFCs and doing RFC reviews" |
| **HashiCorp** | RFC | Well-documented public template |
| **Artsy** | RFC | Used for both technical and cultural changes |
| **BBC iPlayer** | RFC | Engineering decision documentation |
| **Amazon** | PR/FAQ | Different format called "working backwards documents" |
| **Peloton** | Design Docs + ADRs | Evolved approach combining both |

Note: Facebook/Meta is notably minimal in its documentation culture compared to other Big Tech companies.

### Why Companies Adopt RFC Processes

1. **Scaling knowledge**: As teams grow, verbal communication doesn't scale
2. **Eliminating silos**: RFCs spread information across organizational boundaries
3. **Better decisions**: Writing forces thorough thinking
4. **Asynchronous collaboration**: Distributed teams can participate regardless of timezone
5. **Creating accountability**: Written proposals create commitment
6. **Building history**: New team members can understand past decisions

### Evolution: The Uber Story

Uber's RFC process illustrates how companies adapt over time:

1. **Early Days (DUCK format)**: Simple documents for a small engineering team
2. **Growth Phase (RFC)**: Evolved format with segmented mailing lists by engineering group (Backend, Web, Mobile) and "approver" fields for complex proposals
3. **Scale Challenges (2,000+ engineers)**: Hundreds of RFCs weekly caused noise; ambiguity about when RFCs were needed; discoverability problems with Google Docs storage
4. **Adaptation**: Introduced lightweight templates for team-scope changes and heavyweight templates for organization-wide impacts

---

## RFC Templates and Formats

### Common RFC Sections

Most RFC templates include these core sections:

| Section | Purpose |
|---------|---------|
| **Summary/Overview** | 1-2 paragraphs explaining the RFC's goal |
| **Background/Context** | Full context so newcomers can understand |
| **Problem Statement** | Why this change is needed |
| **Motivation** | Why now? Why this approach? |
| **Proposal/Solution** | The "how" of the proposed solution |
| **Detailed Design** | Technical implementation details |
| **Alternatives Considered** | Other approaches and why they were rejected |
| **Risks/Drawbacks** | Potential downsides and mitigations |
| **Open Questions** | Unresolved issues that won't block approval |
| **FAQ** | Common questions and answers |

### The HashiCorp RFC Template

HashiCorp has published a well-regarded RFC template with these key principles:

**Overview Section**: Should be one or two paragraphs explaining the goal without diving into "why", "why now", or "how".

**Background Section Litmus Test**:
> "If you can't show a random engineer the background section and have them acquire nearly full context on the necessity for the RFC, then the background section is not full enough."

**Proposal Section**: Given the background, this section proposes a solution—an overview of the "how".

**Implementation Section**: Details rough API changes (internal and external), package changes, etc. The goal is to give reviewers an idea about subsystems requiring change and the surface area of those changes.

### The Phil Calcado Structured RFC Template

Phil Calcado (who has implemented RFC processes at ThoughtWorks, SoundCloud, DigitalOcean, and Meetup) uses a format based on the NABC value proposition framework:

- **Title and metadata header**
- **Need**: What problem are we solving?
- **Approach**: How will we solve it?
- **Benefits**: What do we gain?
- **Competition/Alternatives**: What else did we consider?

Key insight: "Every RFC should consider the alternative of doing nothing, as every change requires investment of time, energy, and resources."

### The Rust RFC Template

Rust's RFC template is widely influential in open source. Key sections:

- **Summary**: Brief explanation of the feature
- **Motivation**: Why are we doing this? What use cases does it support?
- **Detailed Design**: Technical specification in sufficient detail that reviewers can understand interactions with other features
- **Drawbacks**: Why should we *not* do this?
- **Prior Art**: How do other languages/projects handle this?
- **Unresolved Questions**: What aspects need to be resolved before implementation?
- **Future Possibilities**: What related ideas might be enabled by this work?

### Lightweight vs Heavyweight Templates

Organizations often develop multiple template tiers:

**Lightweight Templates** (for team-scope changes):
- Problem statement
- Proposed solution
- Brief impact analysis

**Heavyweight Templates** (for organization-wide impacts):
- Full background and context
- Detailed design and implementation plan
- Comprehensive alternatives analysis
- Risk assessment
- Migration strategy
- Success metrics

---

## RFC Lifecycle and Workflow

### Typical RFC Statuses

| Status | Description |
|--------|-------------|
| **Draft/In Preparation** | Author is writing, not yet ready for review |
| **Pending/In Review** | RFC submitted for feedback, comment period active |
| **Approved/Accepted** | RFC has been approved, ready for implementation |
| **Active** | RFC is being implemented |
| **Landed/Completed** | Implementation shipped in production |
| **Rejected** | RFC was not approved |
| **Withdrawn** | Author withdrew the RFC |
| **Superseded/Obsolete** | Replaced by a newer RFC |

### The Standard Workflow

1. **Drafting**
   - Author identifies a problem or opportunity
   - Author writes initial RFC using organization's template
   - Author may seek informal feedback from close colleagues

2. **Informal Review (Optional)**
   - Share with a small group for early feedback
   - Pair less-experienced authors with senior engineers as "backers"
   - Iterate on the document before broader distribution

3. **Formal Submission**
   - Submit RFC to designated channel (mailing list, GitHub PR, Confluence, etc.)
   - Announce to relevant stakeholders
   - Begin formal comment period

4. **Comment Period**
   - Stakeholders read and provide feedback
   - Author responds to questions and concerns
   - Document may be revised based on feedback
   - Typical duration: 2 days to 1 week (varies by organization)

5. **Decision**
   - Designated decision-maker(s) approve or reject
   - May require explicit sign-off from approvers
   - Decision and rationale are recorded

6. **Implementation**
   - If approved, work begins on implementation
   - RFC serves as reference during development
   - Changes to the plan may require RFC amendments or new RFCs

7. **Archival**
   - Completed RFCs are archived for future reference
   - Status is updated to reflect completion

### Comment Period Best Practices

- **Set clear deadlines**: Proposals shouldn't linger forever
- **Minimum duration**: At least 2 days for meaningful feedback
- **Maximum duration**: Typically 1 week; longer for major changes
- **Seed early discussions**: The first proposals may be quiet; consider designating trusted people to provide initial feedback

### Decision-Making Clarity

A crucial element often missing from naive RFC implementations is a clear decision-making framework. RFCs are a "document and discuss" framework—not inherently a decision-making framework.

**The Problem**: Without explicit decision-making steps, the default outcome of an RFC becomes "no"—leading to inaction and endless discussion.

**The Solution**: Clearly define:
- Who has authority to approve/reject
- What constitutes sufficient review
- How to resolve disagreements
- When the comment period ends

---

## Tools and Ecosystem

### Document and Collaboration Tools

Most organizations use existing collaboration tools rather than specialized RFC software:

| Tool Type | Examples |
|-----------|----------|
| **Cloud Documents** | Google Docs, Dropbox Paper, Notion, Coda, Quip |
| **Git-based** | GitHub/GitLab/Bitbucket with Markdown files |
| **Wikis** | Confluence, Notion, Slab |
| **Hybrid** | Knowledge bases synced with Git (e.g., Guru) |

### Git-based RFC Management

Git repositories are popular for RFC management because they provide:

- Version history of all changes
- Code review tools for discussing proposals
- Pull request workflows for formal submission
- Searchability and discoverability
- Same tooling developers already use

**Example Workflow**:
1. Copy RFC template to new file (`0000-my-feature.md`)
2. Fill in the template
3. Submit as a pull request
4. Discussion happens in PR comments
5. Merge when approved (file renamed with assigned number)

### Notable RFC GitHub Repositories

- **[rust-lang/rfcs](https://github.com/rust-lang/rfcs)**: The influential Rust RFC process
- **[jakobo/rfc](https://github.com/thecodedrift/rfc)**: Template for company-internal RFC processes
- **[kieranpotts/rfcs](https://github.com/kieranpotts/rfcs)**: Generic RFC process template

### Specialized Tools

While most teams use general-purpose tools, some specialized options exist:

- **Talo**: CLI for ADRs, RFCs, and custom design documents
- **Custom internal tools**: Large companies often build bespoke RFC management systems
- **Knowledge management integrations**: Tools like Guru that sync with Git for better discoverability

### Discoverability Solutions

A common problem at scale is finding existing RFCs. Solutions include:

- **Centralized indexes**: Wiki pages or README files linking to all RFCs
- **Tagging/categorization**: Metadata to enable filtering
- **Search tools**: Full-text search across RFC content
- **Knowledge bases**: Tools like Notion or Confluence that provide better search than raw Git
- **Regular digests**: Periodic summaries of new and notable RFCs

---

## Best Practices

### Writing Effective RFCs

1. **Start with the problem, not the solution**
   - The motivation section should make the problem crystal clear
   - A random engineer should understand why this matters

2. **Focus on "what" and "why", less on "how"**
   - Implementation details are better left to those doing the work
   - Avoid bikeshedding discussions about minor details

3. **Be specific about context**
   - Include organizational situation, business priorities, team constraints
   - Link to related documents, previous discussions, relevant ADRs

4. **Always consider alternatives**
   - Every RFC should consider "do nothing" as an alternative
   - Present rejected alternatives and explain why they were rejected
   - Avoid "dummy alternatives" that exist only to make the preferred option look good

5. **Document risks honestly**
   - List potential downsides and failure modes
   - Include security, complexity, compatibility concerns
   - Explain mitigation strategies

6. **Keep scope focused**
   - One decision per RFC
   - Split complex proposals into multiple RFCs if needed
   - Large RFCs are harder to review and more likely to stall

7. **Tailor depth to complexity**
   - Simple changes need simple RFCs
   - Overly detailed RFCs for small tasks waste time
   - Under-documented large projects lead to rework

### Running an Effective RFC Process

1. **Define clear ownership**
   - Every RFC needs an author responsible for shepherding it
   - Decision-making authority must be explicit
   - "Disagree and commit" culture works when ownership is clear

2. **Set reasonable timeframes**
   - Comment periods should have deadlines
   - 2-7 days is typical; adjust for complexity
   - Longer periods lead to discussion fatigue

3. **Encourage broad participation**
   - Consider pairing junior engineers with senior "backers"
   - Recognize excellent commenters
   - Invite cross-functional perspectives

4. **Create psychological safety**
   - People need a safe space to propose ideas
   - Feedback should be constructive
   - Rejection of an RFC is not rejection of the person

5. **Manage noise at scale**
   - Segment distribution lists by area/team
   - Use appropriate templates for different scope levels
   - Don't require everyone to review everything

6. **Maintain discoverability**
   - Index and categorize RFCs
   - Make search easy
   - Regularly prune outdated or irrelevant RFCs

### Providing Effective Feedback

1. **Read the whole document before commenting**
   - Understand the full context
   - Your question may be answered later in the document

2. **Comment on substance, not style**
   - Focus on technical merit and business impact
   - Avoid grammar nitpicking (unless it affects clarity)

3. **Suggest alternatives when critiquing**
   - "Have you considered X?" is more helpful than "This won't work"
   - Bring your expertise to bear constructively

4. **Respect the author's expertise**
   - They've likely thought more deeply about this problem
   - Ask questions rather than making assertions

5. **Recognize when synchronous discussion helps**
   - Some comments need more context than text allows
   - Offer to meet if async discussion is going in circles

---

## Anti-Patterns to Avoid

### Process Anti-Patterns

| Anti-Pattern | Description |
|--------------|-------------|
| **No Decision Framework** | RFC process without explicit approval/rejection mechanism leads to endless discussion and inaction |
| **Design by Committee** | Over-engineered process that's unnecessarily slow and bureaucratic |
| **Diffusion of Responsibility** | Engineers use RFCs as "ass-covering" rather than genuine feedback-seeking |
| **Everyone Reviews Everything** | At scale, this overwhelms senior engineers and creates noise |
| **Ambiguous Scope** | Teams don't know when an RFC is required, leading to inconsistent use |
| **Poor Discoverability** | RFCs exist but nobody can find them |
| **Infinite Comment Periods** | No deadlines mean proposals linger without resolution |

### Content Anti-Patterns

| Anti-Pattern | Description |
|--------------|-------------|
| **Implementation Detail Focus** | Too much "how," not enough "what" and "why" |
| **Missing Alternatives** | No serious consideration of other approaches |
| **Dummy Alternatives** | Non-viable options presented to favor the preferred solution |
| **Hidden Risks** | Only positive outcomes mentioned; downsides buried or omitted |
| **Scope Creep** | RFC tries to solve too many problems at once |
| **Bikeshedding Magnet** | Including minor details that invite endless debate |

### Review Anti-Patterns

| Anti-Pattern | Description |
|--------------|-------------|
| **Drive-by Comments** | Quick, unhelpful comments that don't engage with substance |
| **Expertise Blindness** | Treating all opinions equally regardless of relevant experience |
| **Tone Problems** | Async communication loses tone; comments read as harsh |
| **Never Satisfied** | Reviewers who always find one more thing to question |
| **Radio Silence** | No feedback at all, leaving authors uncertain |

### Organizational Anti-Patterns

| Anti-Pattern | Description |
|--------------|-------------|
| **RFC Tax** | Process becomes a barrier rather than an enabler |
| **Elite Access** | Only senior engineers write RFCs; others feel excluded |
| **Cargo Cult** | Adopting RFC process without understanding the purpose |
| **Process as Shield** | "Everyone reviewed it" used to deflect accountability |

### The Jacob Kaplan-Moss Critique

Jacob Kaplan-Moss has argued that RFC processes are a poor fit for most organizations:

> "The crux of the problem with RFC processes in corporate settings is that the process, as designed, doesn't include any sort of decision-making framework. They are a 'document and discuss' framework—and not a decision-making framework. RFCs are written and discussed, but there's no mechanism by which they're formally adopted or rejected."

**Key Issues**:
- Without explicit decision-making, default outcome is "no"
- Discussion tends to run long as organization grows
- Experts are put on even ground with everyone else
- Process is insensitive to expertise

**The Solution**: If adopting an RFC process, explicitly bolt on a decision-making step.

---

## When to Write an RFC

### Good Candidates for RFCs

Write an RFC when:

- **Building something from scratch**: New endpoint, component, system, library, application
- **Impacting multiple teams/systems**: Cross-cutting changes that affect others
- **Defining contracts or interfaces**: APIs, protocols, integration points
- **Adding significant dependencies**: New frameworks, libraries, services
- **Changing established patterns**: Introducing new approaches or replacing existing ones
- **Making irreversible decisions**: Choices that are hard or expensive to undo
- **Needing buy-in**: Changes that require support from people outside your immediate team

### The Impact Test

> "RFCs should be used when a change impacts more than just a team or any other cohesive group of people."

This draws a line on what autonomy means in practice—a safeguard triggered when a team's decision might impact other individuals.

### Signals You Need an RFC

- Multiple teams will be affected
- The change is architecturally significant
- You need input from domain experts outside your team
- The decision will be hard to reverse
- New team members will wonder "why did we do this?"
- There's likely to be disagreement about the approach
- The change has significant cost, risk, or complexity

### Scope Guidance

The breadth of stakeholders should be proportional to the impact:

- **Narrow impact**: Refactoring a module's internal structure → Small group of technical reviewers
- **Moderate impact**: New API affecting partner teams → Relevant team leads and architects
- **Broad impact**: Organization-wide infrastructure change → Engineering-wide visibility

---

## When NOT to Write an RFC

### Skip RFCs for Small Changes

> "For small changes: don't bother. Just make the change."

The effort to write an RFC should be proportionate to the complexity of the task. Common guidance:

- **Trivial changes**: Just do them
- **Team-internal decisions**: Team autonomy applies
- **Well-established patterns**: Following existing standards doesn't need new discussion
- **Reversible experiments**: Quick prototypes and spikes

### Signs You Don't Need an RFC

- Only your team is affected
- The change is easily reversible
- There's already an established pattern to follow
- No one will wonder "why did we do this?"
- The overhead of the RFC process exceeds the value

### The SoundCloud Python Lesson

At SoundCloud, an RFC about cloud migration mentioned in passing that internal tooling would be written in Python. This implementation detail—completely irrelevant to anyone outside the team—sparked a heated debate. Teams had autonomy over their tool choices; the mistake was inviting opinionated people to comment on internal decisions.

**Lesson**: Don't invite feedback on decisions that are legitimately within a team's autonomy.

### Avoiding Over-Process

> "Enforcing [the RFC rule] is seldom necessary. In fact, it is more common that the problem is the other way around: it's not that people need to be told when to write an RFC, they need coaching identifying when this is NOT the best course of action."

---

## RFCs vs ADRs vs Design Documents

### The Fundamental Difference

| Document | Purpose | Timing | Audience |
|----------|---------|--------|----------|
| **RFC** | Gather feedback, build consensus | *Before* decision | Broad, seeks input |
| **ADR** | Record decision made | *After* decision | Future readers, posterity |
| **Design Doc** | Detailed technical specification | During planning | Implementation team |

> "RFC is the brainstorming meeting before a decision. ADR is the official memo after the decision."

### Request for Comments (RFC)

- **Purpose**: Propose changes and gather feedback
- **Timing**: Before the decision is made
- **Content**: Problem statement, proposed solution, alternatives, tradeoffs
- **Outcome**: May be approved, rejected, or substantially modified
- **Audience**: Anyone who might have relevant input

### Architecture Decision Record (ADR)

- **Purpose**: Document a decision that has been made
- **Timing**: After the decision is finalized
- **Content**: Context, decision, consequences
- **Outcome**: Records history; immutable once accepted
- **Audience**: Future team members who need to understand "why"

### Design Document

- **Purpose**: Detailed technical specification
- **Timing**: During planning/implementation
- **Content**: Detailed design, APIs, data models, implementation plan
- **Outcome**: Living document updated during implementation
- **Audience**: Implementation team and technical reviewers

### The Natural Flow

A common pattern in organizations using both RFCs and ADRs:

1. **RFC written**: Proposes a change, invites feedback
2. **RFC discussed**: Comments, questions, alternative suggestions
3. **RFC approved**: Decision made to proceed
4. **ADR written**: Records the decision and rationale
5. **Design doc written**: Details the implementation plan
6. **Implementation**: Work proceeds based on approved RFC and design doc
7. **ADR updated** (if needed): Additional ADRs capture implementation decisions

> "The team can start anything by writing an RFC. Then, an accepted RFC can result in multiple ADRs that explain implementation strategies and the architecture of the change."

### When to Use Which

**Use an RFC when**:
- You want to frame a problem and propose a solution
- You want thoughtful feedback from a distributed team
- You want to surface an idea or gather input
- You need to communicate around a cross-functional decision

**Use an ADR when**:
- You've collected feedback on an RFC and decided to move forward
- A team decided on a solution together that doesn't impact anyone else
- You need to record a past decision you still remember
- You want future developers to understand the "why"

**Skip the RFC when**:
- A team decides on a solution together that doesn't impact anyone else
- A few people find a solution without needing to convince the team
- The decision is small and reversible

### The Spotify Approach

Spotify uses both RFCs and ADRs, which are "deeply embedded part of the culture" and sometimes used for non-technical changes such as re-orgs.

Their guidance:
- Write ADRs to backfill undocumented decisions
- Write ADRs after large changes (when RFCs conclude)
- Write ADRs for small decisions to prevent compounding problems

---

## Real-World Examples and Adoption

### Open Source RFC Processes

#### Rust

The Rust RFC process is one of the most influential open-source examples. Key characteristics:

- **Scope**: "Substantial" changes to Rust, Cargo, or Crates.io
- **Process**: Submit RFC as pull request; discussion in PR comments
- **Template**: Detailed template covering motivation, design, drawbacks, alternatives, prior art
- **Decision**: Requires final comment period and core team acceptance
- **Implementation**: RFC acceptance doesn't guarantee implementation priority

Many other projects have based their RFC processes on Rust's, including Ember, React, Vue, Yarn, and ESLint.

#### Other Open Source Projects

- **React**: RFC process for significant changes
- **Vue**: Similar to Rust, adapted for the framework
- **Ember**: Long-standing RFC tradition
- **Yarn**: Package manager RFC process
- **ZeroMQ**: Uses RFCs for protocol and library changes

### Enterprise RFC Implementations

#### Uber

- **Scale**: Evolved from tens to thousands of engineers
- **Format**: DUCK format evolved into RFC with segmented mailing lists
- **Challenges at scale**: Noise, ambiguity, discoverability
- **Adaptations**: Lightweight and heavyweight templates; approver fields

#### Google

- **Name**: Design Docs
- **Culture**: Strong culture of written proposals before major work
- **Characteristics**: Detailed technical documentation with broad review

#### Spotify

- **Approach**: Combined RFC and ADR culture
- **Scope**: Technical and non-technical changes
- **Integration**: "Deeply embedded part of the culture"

#### HashiCorp

- **Contribution**: Publicly shared RFC template
- **Format**: NABC-inspired structure
- **Principles**: Clear background, focused proposals, explicit alternatives

#### Phil Calcado's Implementations

Phil Calcado has implemented structured RFC processes at:
- ThoughtWorks
- SoundCloud
- DigitalOcean
- Meetup

His structured RFC process emphasizes separating decision-making from feedback gathering, clear accountability, and avoiding implementation detail bikeshedding.

### Adoption Patterns

Organizations typically adopt RFC processes when:
- Teams grow beyond the size where verbal communication scales
- Knowledge silos become problematic
- Decision-making becomes inconsistent
- New team members struggle to understand past decisions
- Cross-team coordination becomes difficult

---

## Sources and Further Reading

### Foundational Resources

- [Celebrating 50 Years of the RFCs That Define How the Internet Works](https://www.internetsociety.org/blog/2019/04/celebrating-50-years-of-the-rfcs-that-define-how-the-internet-works/) - Internet Society
- [Request for Comments - Wikipedia](https://en.wikipedia.org/wiki/Request_for_Comments) - Comprehensive overview
- [IETF | RFCs](https://www.ietf.org/process/rfcs/) - Official IETF RFC process documentation
- [RFC 2026: The Internet Standards Process](https://www.rfc-editor.org/rfc/rfc2026.html) - IETF standards process

### Internal/Corporate RFC Processes

- [Scaling Engineering Teams via RFCs: Writing Things Down](https://blog.pragmaticengineer.com/scaling-engineering-teams-via-writing-things-down-rfcs/) - Gergely Orosz
- [Companies Using RFCs or Design Docs and Examples](https://blog.pragmaticengineer.com/rfcs-and-design-docs/) - Gergely Orosz
- [Engineering Planning with RFCs, Design Documents and ADRs](https://newsletter.pragmaticengineer.com/p/rfcs-and-design-docs) - The Pragmatic Engineer Newsletter
- [Software Engineering RFC and Design Doc Examples and Templates](https://newsletter.pragmaticengineer.com/p/software-engineering-rfc-and-design) - The Pragmatic Engineer Newsletter

### Process Design

- [A Structured RFC Process](https://philcalcado.com/2018/11/19/a_structured_rfc_process.html) - Phil Calcado
- [A thorough team guide to RFCs](https://leaddev.com/technical-decision-making/thorough-team-guide-rfcs) - LeadDev
- [Planning for change with RFCs](https://increment.com/planning/planning-with-requests-for-comments/) - Increment
- [6 lessons on using technical RFCs as a management tool](https://opensource.com/article/17/9/6-lessons-rfcs) - Opensource.com

### Templates

- [HashiCorp RFC Template](https://works.hashicorp.com/articles/rfc-template) - Well-structured corporate template
- [Template for writing technical RFC docs](https://www.lambrospetrou.com/articles/rfc-template/) - Lambros Petrou
- [Rust RFC Template](https://github.com/rust-lang/rfcs/blob/master/0000-template.md) - Influential open source template
- [jakobo/rfc](https://github.com/thecodedrift/rfc) - GitHub template for company-internal RFCs

### RFCs vs ADRs

- [ADRs and RFCs: Their Differences and Templates](https://candost.blog/adrs-rfcs-differences-when-which/) - Candost's Blog
- [How and Why RFCs Fail](https://candost.blog/how-and-why-rfcs-fail/) - Candost's Blog
- [Documenting Design Decisions using RFCs and ADRs](https://brunoscheufler.com/blog/2020-07-04-documenting-design-decisions-using-rfcs-and-adrs) - Bruno Scheufler
- [RFC vs. ADR: Why Developers Should Care About Both](https://medium.com/@jashan.pj/rfc-vs-adr-why-developers-should-care-about-both-db886d40de9e) - Medium

### Critiques and Challenges

- [RFC processes are a poor fit for most organizations](https://jacobian.org/2023/dec/1/against-rfcs/) - Jacob Kaplan-Moss
- [Goals and Failure Modes for RFCs and Technical Design Documents](https://medium.com/better-programming/goals-and-failure-modes-for-rfcs-and-technical-design-documents-c4ee1d1da6ff) - Better Programming

### Open Source Examples

- [rust-lang/rfcs](https://github.com/rust-lang/rfcs) - Rust RFC repository
- [The Rust RFC Book](https://rust-lang.github.io/rfcs/) - Rust RFC documentation
- [Transparent Cross-Team Decision Making using RFCs](https://patterns.innersourcecommons.org/p/transparent-cross-team-decision-making-using-rfcs) - InnerSource Patterns

### Historical Context

- [RFC 1 Defines the Building Block of Internet Communication](https://thisdayintechhistory.com/04/07/rfc-1-defines-the-building-block-of-internet-communication/) - This Day in Tech History
- [The Publication of the First RFC](http://scihi.org/steve-crocker-rfc/) - SciHi Blog

---

## Quick Reference: Starting with RFCs

### Minimal RFC Template

```markdown
# RFC: [Title]

## Status
[Draft | In Review | Approved | Rejected | Withdrawn | Superseded]

## Author(s)
[Names]

## Date
[Date submitted]

## Summary
[1-2 paragraphs explaining what this RFC proposes]

## Background/Context
[Why does this problem exist? What's the current situation?]

## Problem Statement
[What specific problem are we solving?]

## Proposal
[What do we want to do? High-level description of the solution]

## Alternatives Considered
[What other approaches did we consider? Why were they rejected?]
- Alternative 1: [Description and why rejected]
- Alternative 2: [Description and why rejected]
- Do nothing: [Why is this not acceptable?]

## Risks and Drawbacks
[What could go wrong? What are the downsides?]

## Open Questions
[What hasn't been figured out yet?]
```

### RFC Process Checklist

1. **Before Writing**
   - [ ] Is this change significant enough to need an RFC?
   - [ ] Who are the stakeholders?
   - [ ] What alternatives exist?

2. **Writing**
   - [ ] Problem is clearly stated
   - [ ] Background provides sufficient context
   - [ ] Alternatives are seriously considered
   - [ ] Risks are honestly assessed
   - [ ] Scope is focused on one decision

3. **Review**
   - [ ] Submitted to appropriate channels
   - [ ] Comment period has deadline
   - [ ] Approvers are identified
   - [ ] Author is responsive to feedback

4. **After Approval**
   - [ ] Decision is recorded (consider writing ADR)
   - [ ] RFC is archived and discoverable
   - [ ] Implementation plan is clear

### Decision Questions

**Do I need an RFC?**
- Does this affect people outside my immediate team?
- Will this be hard to reverse?
- Is there likely to be disagreement?
- Will future team members wonder "why?"

If yes to any of these, consider an RFC.

**Should I write an ADR instead?**
- Is the decision already made?
- Is the scope small and team-internal?
- Do I just need to record what we decided, not gather feedback?

If yes, an ADR may be more appropriate.

---

*Document compiled from research across 30+ sources including IETF documentation, The Pragmatic Engineer newsletter, Phil Calcado's blog, HashiCorp's RFC template, Rust RFC process, and various engineering blog posts from Uber, Spotify, and other technology companies.*
