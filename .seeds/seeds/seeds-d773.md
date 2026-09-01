---
id: seeds-d773
title: Emit compact JSON by default (no indent) — pretty-printing costs tokens for output whose whole purpose is agent consumption
status: resolved
type: idea
created_at: 2026-08-10T16:11:19.717044+00:00
updated_at: 2026-08-31T20:02:48.122049+00:00
resolved_at: 2026-08-11T19:45:26.403588+00:00
resolution: "Shipped in v0.5.0 as seeds-230: `suggest --json` emits compact JSON (separators=(',',':')), 21% smaller on a live query. The JSONL export was deliberately left alone.\n\nEFFICACY — tweaking needed: NONE. Implemented exactly as the bead specified, first attempt, no surprises.\n\nWhat made it work: measuring before writing the bead rather than after. The audit found exactly one CLI JSON site — and it was the one whose help text said 'Emit JSON for agent piping' while pretty-printing. The three-level measurement (indent=2 599 / no-indent 453 / tight separators 415) is what stopped the bead from specifying 'remove indent=2', which would have looked done while leaving ~8% on the table.\n\nCarry forward: an audit that produces a NUMBER produces a precise bead. 'Compact the JSON' would have shipped something worse."
tags:
  - json
  - output
  - token-efficiency
  - cli
  - agent-ux
relationships:
  - target_id: seeds-142.1
    rel_type: relates-to
    created_at: 2026-08-10T16:11:26.603817+00:00
  - target_id: seeds-137
    rel_type: relates-to
    created_at: 2026-08-10T16:11:26.740084+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

@aguynamedryan, after looking at the headroom CLI project (not located on this box — recorded as stated origin, unverified):

> "When we are producing JSON, we should default to compacted JSON as much as possible to reduce token usage. But then, obviously have some sort of switch that allows us to have pretty printed JSON when a human wants it. I mean, honestly, maybe we don't even need that. Maybe we just want it compacted at all times. And someone can just run it through jq when they want a pretty printed version."

## Grounding: the surface area is exactly one site, and it's the ironic one

Audited every JSON emission in `src/seeds/` (2026-08-10):

- **`cli.py:472` — `seeds suggest --json`. THE one that matters.** Emits `json.dumps(payload, indent=2)`. The flag's own help text reads **"Emit JSON for agent piping"** — so the single place we pretty-print is the one whose stated purpose is machine consumption. That is the whole idea in one line.
- `export.py:103` — JSONL export. Already compact (`json.dumps(data, ensure_ascii=False)`, no indent). No change needed; JSONL is line-delimited so it could not be indented anyway.
- `db.py:424,466` — tags serialized into SQLite. Internal storage, already compact, irrelevant.
- `web.py` — emits no JSON (the one `indent` hit there is a docstring about tree rendering).

So the concrete change is a **one-line diff**. The deliberation is about the principle, not the effort.

## Measured, not assumed

`seeds suggest "nix flake installation" --json`, real output:
- pretty (`indent=2`): 406 bytes
- compact (`jq -c`): 292 bytes
- **28.1% reduction**

Small sample, but the ratio is structural (indentation scales with nesting depth × record count), so it should hold or improve on larger result sets. Bytes are a proxy for tokens, not a substitute — worth re-measuring in tokens if this ever grows beyond one call site.

## The actual question: flag, or no flag?

@aguynamedryan's lean is no flag — always compact, `| jq` for humans. Arguments:

**For no flag (his lean):**
- `jq` is already the universal pretty-printer and is installed everywhere we care about. `seeds suggest --json | jq` is muscle memory.
- A `--pretty` flag is surface area to document, test, and keep working, in exchange for something one pipe already does.
- The output is explicitly *for agents*. Optimizing the default for the rare human reader inverts the priority.

**For a flag:**
- Someone without `jq` (a fresh container, a Windows shell) gets a wall of one-line JSON.
- Cheap to add now, awkward to add later if anyone starts parsing our output positionally.

**Third option worth naming:** make it conditional on TTY — compact when piped, pretty when stdout is a terminal. That is what many CLIs do (`git`, `ls`, `jq` itself). It gets both behaviors with no flag at all. Cost: output that changes shape depending on context, which is exactly the kind of thing that surprises someone debugging a pipeline.

## Does this generalize?

Worth deciding as a standing principle rather than a one-off, since the point is to bind FUTURE JSON surfaces too — right now there is only one, so the rule costs nothing to adopt and is cheapest to set before more accumulate. Candidate wording: *"seeds emits compact JSON on every machine-readable surface; humans pipe through jq."* If that is the call, it likely belongs in CLAUDE.md as a trellis rather than only in a seed.

Related: seeds-142.1 (originated `seeds suggest`, and explicitly asked "JSON output mode for agent piping?" — this is the follow-through on that surface), seeds-137 and seeds-138 (the output-economy family: compact modes, fold thresholds, token cost of tool output), seeds-38 (JSON vs markdown token efficiency for LLM consumption).


---

## Measurement refinement (2026-08-10): "compact" has two levels

Python's `json.dumps` without `indent` still emits `", "` and `": "` separators. True compactness needs `separators=(",", ":")`. Measured on a representative payload:

| form | bytes |
|---|---|
| `indent=2` (today) | 599 |
| no indent, default separators | 453 |
| `separators=(",", ":")` | 415 |

So dropping `indent` captures most of the win (~24%), and tight separators buys another 8.4% on top. The bead should specify the tight form explicitly — "remove indent=2" alone leaves value on the table.

## Correction: the JSONL export is NOT maximally compact — and should stay that way

The audit above said `export.py:103` was "already compact. No change needed." That is true only relative to indentation. It calls `json.dumps(data, ensure_ascii=False)` with **default separators**, so every line carries `", "` and `": "` padding.

Measured on the real tracked export (268 seeds, 520,070 bytes): fully compacting would save **9,154 bytes (1.8%)**.

**Decision: leave it alone.** Reasons, in order of weight:
1. It would rewrite **every line** of a git-tracked 520KB file — an enormous one-time diff across the entire deliberation history, permanently muddying `git log -p` and `git blame` on `.seeds/seeds.jsonl`.
2. The JSONL is a sync/export artifact and the source of truth for round-trip import — not agent-facing output. Nothing pipes it into a context window wholesale; agents read seeds via `seeds show` / `seeds suggest`. So the token-economy argument that motivates this seed does not actually apply to it.
3. 1.8% is a rounding error against that churn.

The token argument applies to output an LLM *reads*, which is exactly `suggest --json` and nothing else today. Worth stating explicitly so a future agent doesn't "finish the job" by compacting the export.



---

## Promoted to beads (2026-08-10)

- **seeds-230** (P3, task) — Emit compact JSON from `seeds suggest --json` (no indent, tight separators). This is a BEAD id, not a seed id. Carries the locked decisions: always compact with no `--pretty` flag (@aguynamedryan's call, quoted verbatim), TTY-conditional explicitly rejected, and `separators=(",", ":")` rather than merely dropping `indent`. Scope-fenced against the JSONL export, the SQLite tag storage, and the Flask routes.

**Still open in this seed, deliberately not promoted:** whether "seeds emits compact JSON on every machine-readable surface; humans pipe through jq" becomes a standing principle binding future JSON surfaces. That is a trellis question (CLAUDE.md), not a task — and it is cheapest to settle while there is still only one call site.
