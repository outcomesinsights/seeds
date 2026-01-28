# Decision-Making and Deliberation Tools

**Created:** 2026-01-22
**Context:** Research for ADRB tooling - surveying existing and historical tools for capturing deliberation and decision rationale

---

## Table of Contents

1. [The Forgotten 1970s-80s Lineage](#the-forgotten-1970s-80s-lineage)
2. [Tools Available Today](#tools-available-today)
3. [Key Historical Observations](#key-historical-observations)
4. [Relevance to ADRB](#relevance-to-adrb)
5. [Sources](#sources)

---

## The Forgotten 1970s-80s Lineage

The IBIS/design rationale field had a rich flourishing in the 1970s-80s that largely fell by the wayside. Much of this work predates the web and modern version control, yet addressed many of the same problems we face today.

### The Rittel Lineage (1970s)

| Tool | Year | Description |
|------|------|-------------|
| **IBIS** | 1970 | Kunz & Rittel's paper-based system. Originally used in government agencies and universities. The foundational work. |
| **PROTOCOL** | 1970s | First computerized Rationale Management System supporting PHI (Procedural Hierarchy of Issues) |
| **STIEC** | 1970s | Hans Dehlinger's first IBIS software system |
| **MIKROPLIS** | 1982 | Raymond McCall's PC implementation using PHI. Hypertext software for handling textual information representing designers' reasoning. |
| **Rittel's unnamed system** | 1983 | Small system built by Rittel himself (unpublished) |

**Raymond McCall** is a key figure - he created the first hypertext systems for design rationale in the 1970s-80s and was the first to integrate rationale capture into 3D CAD systems. His PhD dissertation introduced PHI (Procedural Hierarchy of Issues), a refinement of IBIS.

### Xerox PARC Era (1980s)

#### NoteCards (1984)

Developed by Frank Halasz, Randall Trigg, and Thomas Moran at Xerox PARC.

- Hypertext-based personal knowledge base system
- Implemented in LISP on D-machine workstations with large, high-resolution displays
- Physical card metaphor - each card displays content in a separate window
- Over 40 node types supporting various media
- Fully customizable via LISP - authors could create entirely new node types
- Designed to help transform "chaotic collection of unrelated thoughts into an integrated, orderly interpretation of ideas"

Randall Trigg completed the first-ever PhD thesis on hypertext in 1983 at University of Maryland before joining PARC.

**Historical note:** Video demonstrations from January 8, 1985 featuring Tom Moran and Frank Halasz are available on the Internet Archive.

Frank Halasz's 1988 paper "Seven Issues for the Next Generation of Hypermedia Systems" (Communications of the ACM) remains influential and is still cited as prescient about hypertext's future.

#### QOC - Questions, Options, Criteria (1991)

Developed by Allan MacLean, Richard Young, Victoria Bellotti, and Thomas Moran at Rank Xerox EuroPARC.

- Semiformal notation for Design Space Analysis
- **Questions** highlight key issues in the design space
- **Options** are possible answers to questions
- **Criteria** are reasons that argue for or against options
- Relationships shown as positive (solid line) or negative (dotted line)
- Options can spawn consequent questions for detailed exploration

Purpose: Support both original design process and subsequent redesign/reuse by providing explicit representation for reasoning about design consequences.

### Late 1980s Tools

#### gIBIS - Graphical IBIS (1987-88)

Developed by Jeff Conklin and Michael Begeman at MCC (Microelectronics and Computer Technology Corporation) in Austin, Texas.

- Graphical hypertext IBIS implementation
- Color-coded nodes for issues, positions, and arguments
- Directed links to enforce IBIS rhetorical rules
- Relational database backend for scalability
- Multi-user access
- Four fixed windows: map (global and local), index, node contents, control panel
- Features: clusters (subnets), context-sensitive menus, multiple indexes, user configurations, link filtering, simple queries, pointers to external objects

gIBIS addressed limitations in IBIS's manual, paper-based approach by leveraging emerging hypertext technologies.

#### Other Late 1980s Systems

| Tool | Description |
|------|-------------|
| **MicroIBIS** | Hashim's Turbo Prolog implementation. Included maps, anchors, clusters, versioning, filters, user configuration, node attributes. **Source code was published.** |
| **HyperIBIS** | Late 1980s IBIS implementation |
| **PHIDIAS** | McCall's system integrating rationale capture with 3D CAD. Like MIKROPLIS, supported authoring, indexing, and retrieval of hierarchically-structured discussions using PHI. |
| **AAA (Author's Argumentation Assistant)** | ~1990. Combined PHIBIS model with Toulmin model of argumentation. Hypertext-based authoring tool for argumentative texts. |

### The gIBIS → QuestMap → Compendium Lineage

1. **gIBIS** (1987-88) - Research prototype at MCC
2. **QuestMap** - Commercial software that emerged from gIBIS success
3. **Compendium** (mid-1990s onward) - Al Selvin and Maarten Sierhuis at NYNEX Science & Technology, joined by Conklin, Simon Buckingham Shum, and others. Released as open source in 2009.

---

## Tools Available Today

### Still Downloadable (Unmaintained)

#### Compendium

- **Status:** Open source (LGPL), no longer actively maintained
- **Download:** https://cognexus.org/download_compendium.htm
- **Platform:** Java-based, works on modern systems
- **Lineage:** Direct descendant of gIBIS → QuestMap

The most complete IBIS implementation still available. Adds hypertext functionality and database interoperability to IBIS notation.

Features:
- Diagrammatically represents thoughts as labeled icon nodes
- Node types: issues/questions, ideas/answers, arguments, references, decisions
- Applications: issue mapping, design rationale, requirements analysis, meeting management, action tracking

Can be used with **dialogue mapping** facilitation method.

### Actively Developed

#### Argdown

- **Website:** https://argdown.org/
- **Source:** https://github.com/christianvoigt/argdown
- **Status:** Active, open source

Markdown-inspired syntax for complex argumentation. Not software itself, but a syntax - a lightweight markup language.

**Key insight:** Designed for the "Markdown generation" - text-based, version-controllable, embeddable.

Available tools:
- **VS Code Extension** - Full language support with live preview, syntax highlighting, content assist, code linting, export options
- **Browser Sandbox** - Try Argdown with live preview
- **CLI Tool** - Define custom processes, export multiple argument maps
- **Obsidian Plugin** - Syntax highlighting, real-time previews, multiple Argdown blocks per file

Features:
- Argument maps generated while typing
- Export to PDF, web components, images
- Can be embedded within Markdown
- Includes ArgVu font with Argdown-specific ligatures

#### Kialo / Kialo Edu

- **Website:** https://www.kialo.com/ (general) / https://www.kialo-edu.com/ (education)
- **Status:** Active, proprietary
- **Founded:** 2011

The world's largest argument mapping and structured debate site. Name is Esperanto for "reason."

Structure:
- Argument maps as debate trees
- Hierarchical branches with thesis as root
- Arguments (pros) and counterarguments (cons) branch from central thesis

2024 updates:
- Small Group Mode for educators
- LMS integrations (Canvas, Moodle, Blackboard, Google Classroom)

Research backing: Multiple empirical studies show argument-mapping activities are among the most effective methods for teaching critical thinking, with one study showing computer-based argument mapping "more than tripling absolute gains made by other methods."

#### Other Modern Tools

| Tool | Description |
|------|-------------|
| **Argunet** | Open-source argument mapping. Started 2006, published 2007 (Free University Berlin). Downloaded 50,000+ times. http://www.argunet.org |
| **Vithanco** | Modern tool supporting IBIS notation |
| **DebateGraph** | Alternative to Kialo |
| **Loomio** | Open-source decision-making software for consent-based decisions |

### Restricted/Internal Access

#### DRed (Design Rationale editor)

- **Developed by:** Cambridge Engineering Design Centre
- **Status:** Research prototype, primarily internal to Rolls-Royce
- **Not publicly available**

IBIS-based tool with color-coded status (amber=open, green=resolved).

Key features:
- Assists designers in structuring design thinking
- Captures rationale graphically as designers solve problems
- Reduces need for written reports
- Graph of nodes linked with directed arcs
- Node types include issue, answer, argument

Industrial deployment:
- Installed as standard PLM tool-set on Rolls-Royce technical PC network since November 2005
- Embedded in Generic System Design Process across all R-R engineering staff
- Played key role in two major aerospace incident investigations (2008-2013)
- Used in design of Trent XWB engine for Airbus A350

---

## Key Historical Observations

### The Adoption Problem

Over 1000 papers have been written on design rationale, most referencing Rittel. Yet the tools never achieved mainstream adoption.

**Possible reasons:**
- Too heavyweight for casual use
- Wrong platforms (proprietary workstations, LISP machines)
- Academia-focused rather than practitioner-focused
- Capture overhead vs. benefit timing gap (effort now, benefit later during maintenance/redesign)
- Integration challenges with existing workflows

### What Worked

- **Rolls-Royce + DRed** shows that when rationale capture is embedded in organizational process and tooling, it can succeed at scale
- **Kialo** succeeded by being web-native, social, and education-focused
- **Argdown** is gaining traction by being text-first and integrating with developer tools (VS Code, Obsidian)

### Lost Artifacts Worth Investigating

1. **MicroIBIS source code** - Published in Turbo Prolog. Could potentially be studied/revived for historical understanding.

2. **NoteCards documentation and videos** - Available on Internet Archive. Shows sophisticated hypertext concepts predating the web.

3. **Raymond McCall's body of work** - 30 years of design rationale research, synthesized in "Rationale-Based Software Engineering" book.

4. **Frank Halasz's "Seven Issues" papers** - 1988 and 1991 versions analyzing hypermedia futures.

---

## Relevance to ADRB

### Lessons for ADRB Design

1. **Lightweight capture is essential** - Tools that require significant overhead during active work don't get used. Capture must be nearly frictionless.

2. **Text-first enables integration** - Argdown's success comes from fitting into existing text-based workflows (Markdown, VS Code, git). ADRB's CLI approach aligns with this.

3. **The IBIS grammar is proven** - Issues → Positions → Arguments (pros/cons) has survived 50+ years. Worth adopting.

4. **Separate exploration from decision** - The historical tools distinguish between the deliberation process and the final decision record. This matches our insight about ADRs capturing outcomes, not journeys.

5. **Status tracking matters** - DRed's amber/green (open/resolved) status was key to its utility. Questions/issues need lifecycle states.

### Argdown as Potential Integration

Argdown is the most interesting candidate for integration or inspiration:

- Text-based (fits CLI/git workflows)
- Open source
- Actively maintained
- Obsidian plugin (knowledge management integration)
- Designed for version control

Could ADRB questions/deliberation be stored in Argdown syntax? Or export to Argdown for visualization?

### Compendium for Reference

Worth downloading Compendium to understand what a full IBIS implementation looks like, even if unmaintained. It represents the accumulated wisdom of the gIBIS → QuestMap lineage.

---

## Sources

### IBIS and History
- [Issue-based information system - Wikipedia](https://en.wikipedia.org/wiki/Issue-based_information_system)
- [Horst Rittel - Wikipedia](https://en.wikipedia.org/wiki/Horst_Rittel)
- [Why Horst W.J. Rittel Matters - Dubberly](https://www.dubberly.com/articles/why-horst-wj-rittel-matters.html)
- [IBIS: A Tool for All Reasons (PDF)](http://www.cognexus.org/IBIS-A_Tool_for_All_Reasons.pdf)
- [The what and whence of IBIS - Eight to Late](https://eight2late.com/2009/07/08/the-what-and-whence-of-issue-based-information-systems/)
- [20+ years on from gIBIS and QOC](https://mccricks.wordpress.com/2011/12/02/20-years-on-from-gibis-and-qoc/)

### NoteCards and Xerox PARC
- [NoteCards - Wikipedia](https://en.wikipedia.org/wiki/NoteCards)
- [Reflections on NoteCards: Seven Issues - ACM](https://dl.acm.org/doi/abs/10.1145/48511.48514)
- [NoteCards demo video 1985 - Internet Archive](https://archive.org/details/Xerox_PARC_Notecards_Tom_Moran_and_Frank_Halasz_1985-01-08)

### QOC and Design Space Analysis
- [Questions, Options, and Criteria - Taylor & Francis](https://www.tandfonline.com/doi/abs/10.1080/07370024.1991.9667168)
- [Design Space Analysis - NAVER LABS Europe](https://europe.naverlabs.com/history/past-research/design-space-analysis/)

### Raymond McCall and PHI
- [Raymond McCall - ResearchGate](https://www.researchgate.net/profile/Raymond-Mccall)
- [Rationale-Based Software Engineering (book)](https://books.google.com/books/about/Rationale_Based_Software_Engineering.html?id=AlEFaus8k84C)

### DRed
- [A Tool for Capturing Design Rationale - Design Society](https://www.designsociety.org/download-publication/24055/A+TOOL+FOR+CAPTURING+DESIGN+RATIONALE)
- [DRed 2.0 Paper (PDF)](https://www.designsociety.org/download-publication/28740/DRED+2.0)
- [Cambridge REF Impact Case Study](https://impact.ref.ac.uk/casestudies/CaseStudy.aspx?Id=14057)

### Modern Tools
- [Compendium Download](https://cognexus.org/download_compendium.htm)
- [Compendium - Wikipedia](https://en.wikipedia.org/wiki/Compendium_(software))
- [Argdown](https://argdown.org/)
- [Argdown - GitHub](https://github.com/christianvoigt/argdown)
- [Kialo - Wikipedia](https://en.wikipedia.org/wiki/Kialo)
- [Kialo Edu](https://www.kialo-edu.com/)
- [Argunet](http://www.argunet.org)

### Research and Analysis
- [Hypermedia support for argumentation-based rationale (PDF)](https://www.academia.edu/2655542/Hypermedia_support_for_argumentation_based_rationale_15_years_on_from_gIBIS_and_QOC)
- [Argument map - Wikipedia](https://en.wikipedia.org/wiki/Argument_map)
- [Design rationale - Wikipedia](https://en.wikipedia.org/wiki/Design_rationale)
- [Visualizing Argumentation (PDF)](https://www.researchgate.net/publication/258143455_Visualizing_Argumentation_Software_Tools_for_Collaborative_and_Educational_Sense-Making)

---

*This document surveys tools for capturing deliberation and decision rationale, with emphasis on historical IBIS implementations and their modern descendants. The goal is to inform ADRB's design by understanding what has been tried, what worked, and what failed.*
