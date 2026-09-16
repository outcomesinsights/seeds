---
id: seeds-hxvh
title: seeds glean is blind to subagent transcripts — the glob is one level deep
status: captured
type: concern
created_at: 2026-09-16T16:06:50.817253+00:00
updated_at: 2026-09-16T16:08:39.557927+00:00
tags:
  - glean
  - transcripts
  - subagents
  - capture-gap
  - defect
relationships:
  - target_id: seeds-cpkr
    rel_type: relates-to
    created_at: 2026-09-16T16:08:39.351740+00:00
---

`seeds glean` cannot see subagent transcripts, so everything an agent works out in a
dispatched sub-agent is invisible to the capture instrument.

`list_transcripts` (`src/seeds/glean.py:156-175`) resolves the project's transcript
directory and then globs one level:

```
paths = sorted(
    (path for path in directory.glob(f"*{TRANSCRIPT_SUFFIX}") if path.is_file()),
    key=lambda path: path.stat().st_mtime,
)
```

A non-recursive glob. Sub-agent transcripts are written under a `subagents/`
subdirectory of the session, so they match nothing — including under `--all`, which is
supposed to be the historical catch-up pass.

**Why it matters more than it looks.** Dispatching sub-agents is now routine, and the
reasoning that happens inside one is exactly the material glean exists to recover: figures
somebody measured, a constraint stated once, a question raised and dropped. None of it
reaches the corpus except as whatever the parent agent chose to relay — and the glean
skill's own argument for existing is that summarization drops "exact figures, verbatim
user quotes, and things mentioned but never acted on."

Surfaced by the 2026-09-16 adversarial review of \[[seeds-cpkr]\], whose own two reviewers
are an instance: ~11k words of review reasoning, unreachable by glean, preserved only
because the parent extracted the transcripts by hand.

Open question before fixing: recursing the glob would also sweep every sub-agent from
every unrelated task, which may be the wrong default. A `--subagents` flag, or gleaning
sub-agents only for sessions already being gleaned, may be the right shape.
