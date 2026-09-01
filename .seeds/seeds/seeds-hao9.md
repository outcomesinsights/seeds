---
id: seeds-hao9
title: Should a JSONL import be transactional — all records or none — or best-effort with a report of what it refused?
status: resolved
type: question
created_at: 2026-08-28T13:06:03.944464+00:00
updated_at: 2026-08-31T17:55:11.389425+00:00
resolved_at: 2026-08-29T02:11:33.593338+00:00
resolution: "RULED (Ryan, 2026-08-28): best-effort with a loud report. A malformed record is skipped, everything else imports, and the result names exactly what was refused and why — never a silent skip, and never a partial-import-then-abort.\n\nThe deciding argument was 0.7 rather than 0.6. Under files-as-truth every command becomes a parser, so all-or-nothing would mean one malformed file breaks list, show, ready and prime on every invocation. Best-effort-plus-report is the policy that scales to the new storage format, so ruling it this way settles the read policy once instead of twice. It also directly closes the mechanism behind Mark's five weeks (seeds-1x6b): nothing below a bad line is silently lost, because nothing is silently anything.\n\nNote what this replaces: today's behaviour was neither option this question posed — records above the bad line committed and records below did not. That third, unchosen behaviour is what ships until this lands.\n\nAccepted cost: a refused record lingers until someone acts on the report. Mitigated by doctor, which now calls find_divergence and is green exactly when sync succeeds."
relationships:
  - target_id: seeds-1x6b
    rel_type: questions
    created_at: 2026-08-28T13:06:03.948228+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Left open, and less urgent than it looked. An open vocabulary removes the specific poison this report was about — an unrecognized type is no longer malformed — so the all-or-nothing question now applies only to genuinely corrupt records (unparseable JSON, missing required fields). Worth settling on its own evidence rather than on this incident's.

UPDATE 2026-08-28 — new evidence from an adversarial review (verified at HEAD, not taken on report).

The current behavior is NEITHER of the two options this question poses. An unreadable record aborts the import where it stands, so records above it are committed and records below it are not: partial-import-then-abort. Under a transactional answer that is wrong (it should be all-or-nothing); under best-effort it is also wrong (it should skip and continue). So whichever way this lands, today's behavior changes.

A second instance of the same trigger surfaced: SeedStatus kept the eager enum parse that seed_type shed, so a record carrying "status": "in-progress" reproduces @markdanese's outage verbatim. SeedStatus should NOT be opened the way seed_type was — unlike type, status values drive behavior (list's default exclusion of terminal seeds, blocked, ready, the resolve transitions). That makes this question, not an open vocabulary, the whole fix for that class.

Shipped in the meantime, deliberately policy-neutral: MalformedRecordError names the record number, id, failing field, and how many records already landed, so the operator is told the database is partway through. The traceback was indefensible under either answer; the choice itself is still yours.
