# Is There a "Deliberation Software" Revival? — A Six-Month Sweep (Dec 2025 – Jun 2026)

> **What this is.** A companion sweep to the [intent-debt investigation](intent-debt-investigation/), asking a different question: not "is the *why* scarce" but "is *deliberation software as a category* having a revival I'm not aware of?" Produced 2026-06-15 by a multi-agent deep-research harness (5 search angles → 21 sources fetched → 97 claims extracted → 25 adversarially verified, 9 confirmed / 16 killed). Baseline already on file in [`deliberation-tools-research.md`](deliberation-tools-research.md) was treated as known and not re-reported.
>
> **Read the confidence labels.** The two dev-tooling strands rest on primary sources (GitHub API, npm registry, verbatim arXiv text) and are solid. The civic/democratic strand is **under-evidenced here** — almost every concrete signal failed verification due to source rate-limiting during the run. "Failed verification" means *could not confirm*, **not** *disproven*. That gap is the single biggest limitation of this sweep and is flagged throughout.

---

## The one-line answer

**Yes — there is a real surge, but it has mostly colonized the *word* "deliberation" with a different *shape* than seeds.** In the last six months "deliberation software" has come to mean **multi-LLM debate-and-vote ensembles** (agent councils that emit a verdict), not tools that capture a human's reasoning journey. Simultaneously — and more importantly for seeds — the dev-tooling research literature has **independently rediscovered seeds' exact "capture the why" problem**, but is proposing the *post-hoc extraction* solution seeds deliberately rejected. Net: the **problem** is being validated from two directions while seeds' specific **solution shape** (CLI-first, human-reasoning, journey-not-destination, capture-at-decision-time) remains essentially unoccupied.

---

## Strand 1 — The agent-council wave *(HIGH confidence; primary sources)*

This is the loud one, and it's genuinely new. Seeded by **Andrej Karpathy's `llm-council`** (github.com/karpathy/llm-council, **Dec 17 2025**), a cluster of multi-agent "deliberation" tools has erupted, and it now **dominates the emergent meaning of the term** — re-sorting the GitHub `deliberation` topic by recency, the AI-debate cluster outnumbers human/civic deliberation platforms roughly **15:4**.

The exemplars (all dates verified against the GitHub/npm APIs, current to within days of 2026-06-15):

| Tool | What it is | In-window signal |
|------|-----------|------------------|
| **`@antonbabenko/deliberation-mcp`** | MCP server; a `/consensus` loop (≤5 rounds) with 7 expert sub-agents (Architect, Plan Reviewer, Scope Analyst, Code Reviewer, Security Analyst, Researcher, Debugger) that "debate edge cases until they agree"; "models vote, Claude adjudicates" | **v3.5.4** on 2026-06-11; **51 releases** since v1.6.0 (2026-05-17) |
| **`council-of-high-intelligence`** | "18 AI personas deliberate your hardest decisions across multiple LLM providers" → emits a synthesized **Verdict** | **~968 stars / 102 forks**, pushed 2026-05-21 |
| **`claude-synod-debate`** | "Multi-agent deliberation system for Claude Code — 3-vendor heterogeneous ensemble" | pushed 2026-06-07 |
| **`deliberum`** | "Quality-centered peer deliberation runtime for humans, models, and tools" | created 2026-06-10 |
| **`llm-deliberate`** | Explicitly "researches the **deliberation process itself rather than producing final answers**" — but for LLM-vs-LLM consensus via 5 social-choice algorithms (Plurality, Borda, Copeland/Condorcet, Ranked Pairs) | 2025-12-24; maintainer says it **won't be maintained** |

…plus `ghcp-llm-council`, `agora`, `the-quorum`, `gemot`, `tribunal`, `Judica`, `harmonica-mcp` and more.

**Why this matters for seeds, precisely:** these tools take a human question and emit an **AI-synthesized verdict**. They are **destination-oriented** and **machine-reasoning** — the exact opposite of seeds' bet. Two sharp observations:
- `llm-deliberate` proves the **"process, not destination" framing is in the air** — but it's been pointed at *machine* consensus, not *human* reasoning. The vocabulary seeds uses is being claimed for a different target.
- This is a **naming/positioning hazard**: in mid-2026, someone searching "deliberation tool / deliberation MCP" lands in a sea of agent-councils, not journey-capture. seeds' category label now resolves to something else.

---

## Strand 2 — The design-rationale problem, independently rediscovered in dev tooling *(HIGH confidence; primary sources)*

The strongest signal that seeds' *problem* is real and rising — from a corner that has nothing to do with seeds.

**"Architecture Without Architects: How AI Coding Agents Shape Software Architecture"** (arXiv:**2604.04990**, Konrad/Adam/Terrenzi/Ayvaz, University of Southern Denmark, submitted 2026-04-05) diagnoses seeds' exact gap and locates it in AI-generated code, almost verbatim:

> AI-coding-agent architectural choices "remain buried in generated code with **no ADRs, no design documents, no recorded rationale**"; the rationale "exists **implicitly in the agent's reasoning trace**."

Its proposed fix is a "knowledge layer" that would **extract** those decisions from completed reasoning traces and **persist them as ADRs** to "close the documentation gap" — and the paper notes such tooling "does not yet exist." Reinforced by adjacent in-window papers: **Lore** (arXiv:2603.15566, "Decision Shadow") and **"Context Matters"** (arXiv:2604.03826, EASE 2026).

**The seeds-specific read — and it's a validation of your contrarian bets:** academia is converging on the *problem* seeds was built for, but the *solution* it's reaching for is **automated, post-hoc extraction → ADRs** — which is the **inverse of capture-as-you-deliberate**, and is essentially the two approaches you already deliberated and **declined**:
- post-hoc reconstruction from residue = your `seeds-166` (*proactive corpus extraction*, resolved/declined: "reconstructing from residue isn't very helpful");
- conclusion-as-ADR output = the ADR rejection baked into seeds' founding (and `seeds-168`, *seeds is upstream of intent*).

So the field rediscovering the problem *and reaching for the approaches you rejected* is a point in favor of seeds' positioning, not against it. (An unverified-but-thematically-aligned paper, arXiv:2504.20781, reportedly measured LLM-generated design rationale at **high recall / low precision** vs human experts — i.e. LLMs can surface plausible reasoning but can't reliably reconstruct the *actual* deliberation. If it holds up, it's direct ammunition for "capture at decision time rather than regenerate afterward." Treat as unconfirmed.)

---

## Strand 3 — AI-mediated civic deliberation *(LOW confidence here — under-evidenced, NOT disproven)*

There is continued, possibly accelerating activity in AI-mediated *democratic* deliberation (the Habermas Machine lineage), but **this sweep could not verify most of the concrete signals** — they were lost to source rate-limiting, not refuted.

- **Confirmed (medium):** **Tessler et al., "Can AI mediation improve democratic deliberation?"** (arXiv:**2601.05904**, Jan 2026) advances **Fishkin's trilemma** (participation vs. deliberation quality vs. political equality) as an organizing frame, arguing LLMs can process semantic content that Pol.is/Remesh can't. The frame is **propagating** (the Agora paper, arXiv:2603.07339, picks it up as motivation) — the kind of spreading vocabulary a category revival produces. *Caveat:* the trilemma is Fishkin's prior coinage, not new; and a claim that this was a Habermas-Machine-**team** follow-on was **refuted** — do not assert team continuity.
- **Could NOT be confirmed in this run** (plausible, treat as open): a CIP "Global Dialogues" scaling effort; a Mozilla "Democracy × AI" 2026 incubator cohort; an "AI-delegated deliberation"/"Habermolt" deployment (arXiv:2605.24413); an IJCAI-ECAI 2026 "Augmented Democracies" workshop (Bakker keynote); a CHI 2026 panel "AI Agents and the Future of Deliberation." Each returned 0-0 / abstain under rate-limiting.

**Read for seeds:** even at full strength this strand is **human/civic group deliberation** — orthogonal to seeds' dev-tooling, single-thinker capture niche. It matters as evidence that "deliberation + AI" is a hot phrase, not as a competitor. A targeted re-sweep against reachable primary sources (conference program PDFs, funder pages) is the right follow-up if this strand matters to you.

---

## What this means for seeds

1. **The problem is being validated from two independent directions** (dev-tooling research + civic AI) — your premise is no longer idiosyncratic. Same conclusion the intent-debt sweep reached, now from the deliberation-software angle.
2. **The *term* is being colonized.** "Deliberation software" in mid-2026 most loudly means *agent councils that vote*. This is a **positioning problem**, not a product problem — but it's real: discovery via the obvious keyword now lands on a different category.
3. **Your rejected approaches are the ones the field is adopting.** Post-hoc extraction → ADRs (Architecture Without Architects) is exactly what you declined in `seeds-166` and at founding. The destination-oriented "verdict" shape of the agent-councils is exactly what `seeds-168` argues against. seeds is differentiated *by contrast* with the wave.
4. **seeds' exact shape remains unoccupied.** No CLI-first + human-reasoning + capture-at-decision-time competitor surfaced. Problem crowded; solution-shape empty.
5. **No funding signal** specific to deliberation-*capture* (vs. agent-orchestration) survived verification — so "is money flowing to this niche" is unresolved.
6. **One to watch:** `deliberum` ("peer deliberation runtime for humans, models, and tools") is the agent-debate tool most likely to grow *persistence of the deliberation transcript* — if it does, it moves onto seeds' capture turf. Worth a periodic check.

---

## Open questions (carried from the harness)

- Is the AI-civic-deliberation revival actually as broad as the unverifiable signals suggest? Needs a re-sweep against reachable primary sources before relying on it.
- Will any agent-debate tool (deliberum, deliberation-mcp, council-of-high-intelligence) add **journey/transcript persistence** and cross onto seeds' turf?
- Is seeds' exact combination (CLI-first + human-reasoning + capture-at-decision-time) genuinely unoccupied? This sweep suggests yes but warrants a dedicated confirmation pass.
- Is there a VC thesis / funding behind deliberation-*capture* specifically? No signal survived; unresolved.

---

## Method & integrity notes

- **5 angles** → New-tool launches · AI-era deliberation framings · Civic/democratic + AI · Academic (CHI/CSCW/arXiv) · Dev-tooling convergence.
- **21 sources fetched, 97 claims, 25 verified** (3-vote adversarial; 2/3 refutes kills). **9 confirmed, 16 killed.**
- **Asymmetric confidence by design:** dev-tooling claims verified against primary registries/APIs survived; civic-strand claims relying on web pages mostly failed on rate-limiting and were *under-claimed deliberately*. This report does **not** assert the civic-conference/funding revival as established.
- **Time-sensitivity:** a fast GitHub/MCP wave only ~6 months old; star/release counts will drift fast, and several repos (e.g. `llm-deliberate`) are explicitly unmaintained — *in-window activity ≠ durable traction*.

## Sources (verified strand)

- Agent-council wave: [karpathy/llm-council](https://github.com/karpathy/llm-council) · [antonbabenko/deliberation](https://github.com/antonbabenko/deliberation) ([npm](https://www.npmjs.com/package/@antonbabenko/deliberation-mcp)) · [github.com/topics/deliberation](https://github.com/topics/deliberation) · [0xNyk/council-of-high-intelligence](https://github.com/0xNyk/council-of-high-intelligence) · [quantsquirrel/claude-synod-debate](https://github.com/quantsquirrel/claude-synod-debate) · [xuhuanstudio/deliberum](https://github.com/xuhuanstudio/deliberum) · [arvindand/llm-deliberate](https://github.com/arvindand/llm-deliberate)
- Design-rationale revival: [arXiv:2604.04990 "Architecture Without Architects"](https://arxiv.org/html/2604.04990v1) · [arXiv:2603.15566 "Lore / Decision Shadow"](https://arxiv.org/abs/2603.15566) · [arXiv:2604.03826 "Context Matters" (EASE 2026)](https://arxiv.org/abs/2604.03826)
- Civic strand (confirmed): [arXiv:2601.05904 Tessler et al.](https://arxiv.org/pdf/2601.05904) · [arXiv:2603.07339 Agora](https://arxiv.org/abs/2603.07339)
- Civic strand (UNVERIFIED in this run — do not rely): CIP Global Dialogues · Mozilla "Democracy × AI" cohort · arXiv:2605.24413 (AI-delegated deliberation/Habermolt) · IJCAI-ECAI "Augmented Democracies" workshop · CHI 2026 panels · arXiv:2504.20781 (LLM design-rationale precision/recall) · arXiv:2606.04990 (evidence tracing / execution provenance)
