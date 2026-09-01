---
id: seeds-31.2
title: "Meta: Using seeds to document fixing seeds' own usability problem"
status: resolved
type: idea
parent: seeds-31
created_at: 2026-01-28T17:56:56.117770+00:00
updated_at: 2026-01-28T18:18:08.132831+00:00
resolved_at: 2026-01-28T18:18:08.132824+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

## The Bootstrapping Challenge

We discovered seeds show output gets truncated by Claude Code CLI. To fix it, we need to document our deliberation... in seeds. But viewing that documentation triggers the very problem we're fixing.

## How We Worked Around It

1. Used seeds update --append to add content (small enough to work)
2. Created child seeds with structured content
3. Will implement the fix, then can properly review our own deliberation

## Observation

This meta-situation - using a tool to document improvements to itself - is exactly what seeds should excel at. The tool should support its own evolution.

## User Quote

'How did we end up in a situation where seeds show writes to an output file and prints the path? That isn't obvious, but it's the path we chose because of problems we're working around. Seeds is designed to capture questions, answers, research, and conclusions that led to the decision.'
