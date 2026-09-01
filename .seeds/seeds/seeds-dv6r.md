---
id: seeds-dv6r
title: Files-as-truth puts the seed store inside every repo tool's default scope, and ruff reached into it within minutes
status: captured
type: concern
created_at: 2026-09-01T05:23:43.302048+00:00
updated_at: 2026-09-01T05:24:08.678446+00:00
tags:
  - storage
  - files-as-truth
  - tooling
  - ruff
  - scope
  - canonicality
  - 2026-09-01
relationships:
  - target_id: seeds-sdhc
    rel_type: relates-to
    created_at: 2026-09-01T05:24:08.547579+00:00
  - target_id: seeds-fkb8
    rel_type: relates-to
    created_at: 2026-09-01T05:24:08.677796+00:00
---

Found within minutes of converting the real store, 2026-09-01, by the post-conversion gate rather than by anyone predicting it.

## What happened

`ruff format --check .` went red on `.seeds/seeds/seeds-154.md`. ruff 0.16 formats **Python code blocks inside markdown**, the seed store is now 308 markdown files, and several seed bodies quote code. Its file count went from 65 to 385 the moment the tree landed.

Had it run with `--fix` rather than `--check`, it would have **rewritten a seed body** — someone's deliberation, edited by a formatter, silently.

Fixed by `extend-exclude = [".seeds/"]` in pyproject.toml.

## Why this is a class, not an incident

The storage plan reasoned carefully about what *seeds* does to the store and never asked what *everything else in the repo* does to it. Under SQLite the store was one gitignored binary and one JSONL line-oriented file that no tool had an opinion about. As markdown in the working tree it is now inside the default scope of every formatter, linter, spell-checker, link-checker, search index, and doc generator the repo will ever acquire.

Three specific costs, in increasing order of how quietly they bite:

1. **Content corruption.** A formatter rewriting a fenced block changes what somebody wrote. There is no way to distinguish "improved formatting" from "edited the record" after the fact.
2. **Byte-canonicality breaks, and idempotence with it.** The conversion's central guarantee is that a second `seeds convert` is byte-identical. A body reformatted by an outside tool no longer matches `render_seed_file`'s output, so the next conversion reports a spurious diff — and `seeds check`'s planned non-canonical-bytes smell (seeds-4co.16) starts firing on files nobody edited.
3. **The failure is invisible in review.** A commit that reformats one code block inside one seed is a small, plausible-looking diff among 308 files.

## What to do about it

- The fix for ruff is done and carries its reasoning at the point of use.
- **Every future repo-wide tool needs the same exclusion**, and nothing enforces that. Candidates already plausible here: prettier, markdownlint, a spell-checker, `nix flake check` if it ever formats.
- Worth considering a positive assertion rather than a growing exclusion list: a check that the store is byte-canonical (which is exactly seeds-4co.16's non-canonical-bytes smell) turns "some tool rewrote a seed" from an invisible corruption into a named finding, whatever the tool was. **That reframes seeds-4co.16 from tidiness to a real defence**, and is an argument for promoting it above P3.

## The general shape, which is this project's recurring one

Moving data into the working tree buys legibility and merge behaviour, and it also enrols the data in every convention that applies to the tree. The plan costed the benefits precisely and did not enumerate the enrolment. Same family as the other gate defects recorded here: a check measuring something adjacent to what it claims to protect.

Relates to seeds-4co.16, seeds-sdhc, seeds-fkb8.
