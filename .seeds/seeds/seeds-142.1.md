---
id: seeds-142.1
title: seeds suggest <text> — purpose-built 'does this already exist?' query
status: resolved
type: idea
parent: seeds-142
created_at: 2026-05-18T15:57:41.278134+00:00
updated_at: 2026-08-31T21:41:37.433993+00:00
resolved_at: 2026-08-31T21:34:29.533140+00:00
resolution: "Shipped as 'seeds suggest' (bead seeds-c4b) with exactly the ranking proposed: bm25 + tag overlap + recency + dynamic noise floor. Efficacy: none; the seed specified it well enough to build directly. Resolving the QUESTION, not the feature's future — whether ranked search survives dropping SQLite is now the one open decision in plans/storage-overhaul.md, and is tracked there rather than by holding this seed open."
tags:
  - feature
  - cli
  - ai-ux
  - dedup
  - gleaning
relationships:
  - target_id: seeds-2
    rel_type: relates-to
    created_at: 2026-05-18T15:58:20.027305+00:00
  - target_id: seeds-130
    rel_type: relates-to
    created_at: 2026-05-18T15:58:20.125048+00:00
  - target_id: seeds-d773
    rel_type: relates-to
    created_at: 2026-08-10T16:11:26.603817+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Problem:** When incorporating candidate items from a transcript, Claude needs to ask 'is there already a seed about this?' for each item. Current options:
- `seeds search 'keyword'` — requires Claude to guess the right FTS5 keyword (often misses on phrasing differences)
- `seeds list` and scan — works but doesn't rank or filter by relevance
- grep the JSONL — same problems

**Proposed command:** `seeds suggest <text>` returns top-N existing seeds ranked by relevance to <text>.

**Ranking approach (cheap, no embeddings):**
- FTS5 score across title + content (auto-tokenized from the natural-language input)
- Boost by tag overlap (if text mentions 'compare', boost seeds tagged compare)
- Optional: boost recently-updated seeds (momentum)
- Return top 5-10 with: id, status, title, tags, top matched snippet

**Output sketch:**
```
$ seeds suggest 'venn diagram showing overlap between two code sets'
csc-111   ◌ Compare lens — Venn diagram [compare, deferred-lens, venn, viz]
           snippet: '...Venn rendering for two-set compare...'
csc-101.1 ○ Compare diff — hide-overlap filter [compare, filter, deferred]
           snippet: '...show only what differs...'
csc-101   ◐ Compare diff — anchor-relative [compare, ...]
           snippet: '...compare with anchored set...'
```

**Why not just search:** `search` requires a single FTS5 expression with operator syntax. `suggest` takes natural-language input and does the keyword extraction internally. Different ergonomics for a different use case.

**Open design questions:**
- Should suggest include resolved/abandoned by default? (probably not — only candidates worth updating)
- Min-relevance threshold to avoid noisy hits?
- JSON output mode for agent piping?



---

**Design decisions (2026-05-18):**

1. **Include resolved/abandoned by default** — reframed from 'what could I update' to 'does this idea exist anywhere in our deliberation history?' If a candidate matches an abandoned seed, the agent should know it was previously rejected (and either reopen, link, or genuinely-create-new with that context). Same for resolved. Status icon in output handles visual filtering. Add `--open-only` to restrict to actionable seeds when needed.

2. **Dynamic min-relevance floor** — drop anything below ~half the top-result score. Avoids surfacing noise hits when the candidate is genuinely novel.

3. **JSON output mode** — `--json` emits id/status/title/tags/snippet/score per result for agent piping.


---
**Clancey datapoint (2026-06-05) — see seeds-156:** semantic "does this already exist?" is cheap and dependency-light — Clancey's whole semantic layer is a ~30MB local MiniLM (Xenova/all-MiniLM-L6-v2, 384-dim) with brute-force cosine in-process, no vector DB. Viable in Python (sentence-transformers / onnxruntime). Pairs with the FTS5 + tag-overlap ranking already proposed here rather than replacing it.

SHIPPED (bead seeds-c4b) as `seeds suggest`, with the ranking this seed proposed: bm25 across title+content, tag-overlap boost, recency, and a dynamic noise floor (Database.suggest, db.py:1173). NEW SINCE: the storage overhaul puts it at risk. Dropping SQLite drops FTS5, and whether ranked search survives is now the single decision left open in plans/storage-overhaul.md — it blocks phase 5. Two measurements point opposite ways: Porter stemming is a real casualty ("merging" stops finding "merge"), but grep tested broader than FTS on a real query, 72 hits vs 77, and found one FTS missed.

RULED (@aguynamedryan, 2026-08-31): suggest is removed in the storage overhaul rather than reimplemented. Evidence gathered before agreeing: roughly 15 genuine invocations across 5 sessions in the entire project transcript history, mostly agent-initiated during dedup passes rather than user-initiated. The FTS5 machinery goes with it — Database.suggest, sanitize_fts_query, and the seeds_fts* tables.
