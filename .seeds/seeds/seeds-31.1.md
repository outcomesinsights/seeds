---
id: seeds-31.1
title: "Decision: seeds show --output-file writes to temp file, returns path"
status: resolved
type: idea
parent: seeds-31
created_at: 2026-01-28T17:56:46.591955+00:00
updated_at: 2026-01-28T18:18:08.035581+00:00
resolved_at: 2026-01-28T18:18:08.035573+00:00
relationships:
  - target_id: seeds-137
    rel_type: relates-to
    created_at: 2026-05-01T16:45:39.931448+00:00
  - target_id: seeds-138
    rel_type: relates-to
    created_at: 2026-05-01T18:02:16.108420+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

## Chosen Solution

Add --output-file flag to 'seeds show' that:
1. Writes full output to a temp file
2. Prints only the file path to stdout

Claude can then use the Read tool on that path, completely bypassing Claude Code's bash output truncation.

## Why This Works

The Read tool doesn't have truncation issues - it reads files directly. The problem is only in how Claude Code displays bash stdout in the terminal.

## Alternatives Considered

1. Truncate content in seeds show with --full flag - REJECTED: solves wrong problem, content is fine
2. Named pipe (FIFO) - Too complex, requires coordination
3. Accept limitation - Poor UX, can't view seed content easily
4. File issue with Claude Code - Already exists (#14694, #10664), but we need a workaround now
