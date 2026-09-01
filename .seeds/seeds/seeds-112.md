---
id: seeds-112
title: "Capture gap: questions must be persisted to disk when they arise, not after they're answered"
status: captured
type: concern
created_at: 2026-02-27T15:59:14.444703+00:00
updated_at: 2026-08-31T20:02:40.445328+00:00
tags:
  - capture-gap
  - ai-ux
  - workflow
  - prime
relationships:
  - target_id: seeds-113
    rel_type: relates-to
    created_at: 2026-02-27T15:59:14.444703+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Observed in a live session: an AI agent was deliberating about the project's one-liner tagline — a genuine open question — but never recorded it as a seeds question. It only created q-92c0 after the answer was already provided by the user from a parallel session, logging it as an immediately-answered item. The question existed only in the conversation context window, never in the durable system. This defeats the entire purpose of seeds.

Questions should be captured the moment they surface, not retroactively after resolution. This is the exact scenario described in the prime guidance ('Capture DURING investigation, not just after') but the agent didn't follow it.

Possible causes:
1. Prime guidance isn't strong enough on this point
2. The agent doesn't know HOW to capture mid-conversation (workflow friction)
3. There's no hook or trigger reminding agents to persist open questions

This is a high-priority concern because it undermines seeds' core value proposition.

---
**Another instance (Feb 27, 2026):** During beta release planning session, detailed five-phase plan was discussed including documentation structure (README sections, CHANGELOG, CONTRIBUTING.md), CI/CD specifics (GitHub Actions matrix, ruff, mypy, pytest-cov), and numerous decisions (full strict mypy, keep .seeds/ public, web UI experimental, PyPI deferred). Only high-level decisions were captured into seeds. The detailed phase breakdown, specific README sections modeled on beads, pre-commit/beads hook integration steps, and most implementation specifics were lost. Had to harvest from the session JSONL file after the fact. This is the exact scenario seed-7ec5 warns about — the cost of mid-conversation capture meant the agent skipped it, and critical planning detail fell through the cracks.

---
**Detailed gap analysis — beta release planning session (Feb 27, 2026):**

What follows is an item-by-item accounting of what the agent captured into seeds vs. what it failed to capture. Everything in the "NOT CAPTURED" list was only recoverable by harvesting the raw session JSONL after the fact.

**CAPTURED in seeds (high-level decisions only):**
- License choice: MIT, pending employer approval (q-c562)
- Repo ownership shift: outcomesinsights org, not personal (q-beb8)
- Phase ordering: docs before CI/CD (noted in seed-81a4 content)
- Quality bar: CI tight enough for Dependabot auto-merge (seed-81a4 content)
- Pre-commit hooks needed: ruff lint, format, pytest (seed-81a4.1)
- Test coverage approach: baseline then fill gaps (seed-81a4.2)
- Dependabot auto-merge after CI solid (seed-81a4.3)
- 17 questions created and answered on seed-81a4

**NOT CAPTURED — recovered only via session harvest:**

1. THE FIVE-PHASE PLAN ITSELF: The actual phase breakdown (Foundation, Code Quality, Documentation, CI/CD, Ship) with 14 numbered steps was never persisted as a seed or child seeds. Only oblique references to "Phase 5" appeared in the content.

2. PHASE 1 SPECIFICS: pyproject.toml metadata details — specific author email, specific classifiers to add, specific URLs format, specific keywords list (deliberation, decision-making, idea-tracker, cli, ai-agent, knowledge-management, brainstorming, seed, exploration). Also: ruff+mypy config goes in pyproject.toml.

3. README STRUCTURE: Entire section list modeled on beads README was discussed and agreed but never captured:
   - One-liner tagline placement
   - Quick demo format (text-based CLI block, NOT screenshots/screencasts)
   - Specific demo script (jot->explore->ask->resolve flow with example output)
   - Installation from GitHub section
   - Usage/commands overview
   - Status section (clearly labeled beta)
   - Experimental web UI note (seeds serve)
   - Acknowledgments section with specific wording about Steve Yegge/beads
   - Contributing section
   - License section

4. ACKNOWLEDGMENTS WORDING: @aguynamedryan provided specific language about beads inspiration — "giving AI agents structured tools to work with (1) improves how agents do their jobs, (2) bridges AI-human communication, and (3) unlocks AI potential that is not accessible through unstructured conversation alone." This exact phrasing was lost.

5. API DOCS DECISION: @aguynamedryan asked about Python equivalent of RDoc. Decision was "thorough docstrings yes, hosted docs site no" for beta. Reasoning: CLI tool not a library, --help is the real API surface, can layer Sphinx later. Never captured as a seed or question.

6. TYPE CHECKING DECISION: @aguynamedryan said "go hog wild with it" — full strict mypy, not gradual. Rationale: structured data models benefit from type checking, modest codebase, guards against agent mistakes. Never captured.

7. RUFF AS UNIFIED TOOL: Decision that ruff replaces black+flake8+isort (handles both linting AND formatting). Never captured.

8. PYTHON VERSION DETAILS: Codebase was scanned and confirmed no 3.13-specific features. Drop to >=3.9 deemed straightforward. Specific versions: 3.9, 3.10, 3.11, 3.12, 3.13. 3.14 excluded as pre-release. Never captured.

9. CI/CD SPECIFICS: GitHub Actions confirmed as platform. Specific checks: pytest+coverage, ruff check, ruff format --check, mypy. NOT needed: PyPI publishing, release automation. Never captured as structured data.

10. PyPI NAME STRATEGY: "seeds" name is taken but abandoned (ecological simulation, last release 2011). PEP 541 for reclamation. Alternatives: seeds-cli, deliberation-seeds. Decision: deferred for beta. Never captured as a seed.

11. REPO HYGIENE DECISIONS: Keep .seeds/ public (dogfooding showcase), keep CLAUDE.md and AGENTS.md public (shows AI-assisted development), keep docs/ and plans/ directories. Each was a distinct decision, none were individual seeds.

12. WEB UI SCOPE: Flask web UI included but marked experimental. Keep web.py and Flask dependency. Document seeds serve as experimental/alpha. Captured only as an answered question, not as a decision seed.

13. CLA DETAILS: Full analysis of CLA options (none, CLA Assistant app, Apache-style). Decision rationale for lightweight approach. Relicensing analysis (can release new versions under different license, cannot retroactively relicense others contributions). Strategy: start MIT, lightweight CONTRIBUTING.md note, formalize later. Mostly lost except for brief question answers.

14. BEADS HOOK INTEGRATION STEPS: Specific 4-step integration pattern was discussed in detail but only referenced as "see CLAUDE.md for the integration pattern" in the seed.

15. COMPETITIVE LANDSCAPE: @aguynamedryan suggested searching GitHub for projects using similar keywords. Deferred but the deferral itself was never captured.

**Pattern observed:** The agent captured WHAT was decided (as answered questions) but almost never captured HOW the decision was reached, what alternatives were considered, or the specific implementation details. This is exactly backwards for a deliberation tool — the journey matters more than the conclusion. 17 questions were created and answered, but each answer was 1-2 sentences. The rich discussion, rationale, examples, and specifics were all lost.

**Scale of the gap:** Roughly 15 distinct decisions/plans were NOT captured at all. The ones that WERE captured lost 80%+ of their context and rationale. The session JSONL was ~517KB of conversation; the seeds captured maybe 5KB of that into structured, durable storage.
