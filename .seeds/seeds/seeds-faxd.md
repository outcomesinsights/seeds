---
id: seeds-faxd
title: "BUG: the divergence refusal's own remediation cannot satisfy the check it advises about — the guard is a prefix test described as containment"
status: resolved
type: concern
created_at: 2026-08-26T18:01:44.591680+00:00
updated_at: 2026-08-31T20:02:48.534454+00:00
resolved_at: 2026-08-26T19:38:40.002421+00:00
resolution: "Fixed in 54057b1 (bead seeds-pfe): guard renamed db_extends_disk, message says BEGIN WITH, remediation prints the --replace form that can actually clear the check; guard behaviour unchanged as ruled. Efficacy: no tweaking, built as written. Lesson that outgrew the seed: the defect class 'guidance that does not match its command' recurred same-day in seeds-3dkj, so finding one instance should trigger a sweep."
tags:
  - bug
  - divergence
  - sync
  - error-message
  - remediation
  - dx
  - data-loss
  - peer-report
  - 2026-08-26
relationships:
  - target_id: seeds-cb6r
    rel_type: relates-to
    created_at: 2026-08-26T18:02:31.415813+00:00
  - target_id: seeds-3dkj
    rel_type: relates-to
    created_at: 2026-08-26T19:28:50.593286+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Reported by a peer session working in the home-manager repo (seeds prefix hm-, 202 records), 2026-08-26. Verified against this codebase before recording; the diagnosis below is sharper than the report.

WHAT THE USER HIT. `seeds sync` correctly refused to export after a divergence, saving the content — that part works and should be preserved. The refusal said:

    hm-ml5: the database's content does not contain the on-disk content (they diverge at character 0)
    # compare, then append the text that only exists on disk
    seeds update <id> -a '<the text from disk>'

They followed it exactly. Sync refused again with the identical message. They verified in Python that the on-disk string was now a genuine substring of the database content — containment held and the check still failed. The only thing that worked was `seeds update <id> --replace -c '<original><new>'`, rebuilding the record with the on-disk text FIRST.

THE ACTUAL DEFECT, confirmed in code. `content_is_covered` (export.py:335-347) is a PREFIX test:
    if db_content.startswith(disk_content): return True
    return db_content.strip().startswith(disk_content.strip())
Its own docstring states the intent correctly — "the database's body **starts with** the file's" — and justifies the strictness with evidence: of 42 content-changing edits across 67 commits, 41 were literal appends, and the one exception was a prepended header, "precisely the kind of edit an operator should be told about." The design is deliberate and good.

Three surfaces describe it as containment instead:
1. the function NAME, `content_is_covered`
2. the docstring's summary line, "Is the on-disk body fully contained in what the database is about to write?" — which contradicts the body of its own docstring three paragraphs later
3. the user-facing message at export.py:349, "the database's content does not contain the on-disk content"

WORSE THAN "MISLEADING" — THE ADVICE IS STRUCTURALLY INCAPABLE OF WORKING. The remediation at cli.py:1340-1342 tells the user to APPEND the disk text. Appending yields db_content + disk_content. For the guard to pass, that result must START WITH disk_content — which requires db_content to start with disk_content, which is exactly the condition that just failed. So following the advice can never satisfy the check, for any input, except the degenerate case where the database body is empty. It is not a wording problem that happens to mislead; it is advice that provably cannot succeed.

Compounding it, the message's parenthetical "(they diverge at character 0)" is the one accurate clue on screen, and it points at prefix semantics — but it sits under prose saying "does not contain," so it reads as noise.

FIX, in the order I would do it:
1. Correct the user-facing wording: "the database's content does not BEGIN WITH the on-disk content." One line, removes the false lead.
2. Replace the remediation with one that can actually work — the `--replace` form with the on-disk text leading, i.e. reconstruct the body as <on-disk text> followed by the database's newer text. This is what the reporter had to derive unaided.
3. Rename `content_is_covered` and fix its summary line so the code stops contradicting itself. The explanatory body of that docstring is excellent and should be kept verbatim.

DO NOT relax the check to genuine containment, which the report offered as a third option. The docstring shows prefix strictness is deliberate and evidence-backed, and the single historical case it caught was a prepend — exactly what containment would let through silently. The guard is right; only its description and its advice are wrong.

TEST TO ADD ALONGSIDE: assert that following the remediation the message prints actually clears the refusal. That is the property that was broken, and no test currently asserts it — the guidance and the guard were free to drift apart.


--- SCOPE RULED (@aguynamedryan, 2026-08-26): build it ---

Promoted to beads for implementation. Confirmed scope: fix the user-facing wording to say BEGIN WITH, replace the remediation with a form that can actually clear the guard (the `--replace` form with the on-disk text leading), rename `content_is_covered` and fix its self-contradicting summary line, and add a test asserting that following the printed remediation actually clears the refusal.

Explicitly NOT in scope: relaxing the guard to genuine containment. The prefix strictness is deliberate and evidence-backed, and containment would silently admit the one historical case it was built to catch.


--- SHIPPED (2026-08-26, commit 54057b1, bead seeds-pfe) ---

Built as ruled, no design drift. `content_is_covered` is now `db_extends_disk`; the refusal says "does not BEGIN WITH"; the remediation prints the `--replace` form with the on-disk text leading. The guard's behaviour is byte-for-byte unchanged, which was the locked decision. Suite went 571 -> 572, ruff/format/mypy clean.

The test that matters is the one asserting the END-TO-END property: it constructs a divergence, captures the remediation the CLI actually prints, applies it, and asserts the subsequent sync succeeds. Nothing had ever asserted that the printed advice and the check agreed, which is exactly why they were free to drift apart.

ONE JUDGMENT CALL made in implementation, worth recording: the rename touched only the two test method names that literally embedded the old identifier (`test_identical_content_is_covered` -> `test_identical_content_extends`, and the appended-content twin). Sibling names like `test_divergent_content_is_not_covered` were left alone since they do not contain the renamed symbol. Defensible, but it means the phrase "covered" survives in test names describing a check no longer called that. Cosmetic; noting it so nobody rediscovers it as a loose end.

EFFICACY. Tweaking needed: none. The bead was built exactly as written and every acceptance criterion passed first time.

But the LESSON from this seed did not stay inside it, and that is the interesting part: the fix shipped alongside seeds-cb6r, whose implementation immediately created a fresh instance of THIS seed's own defect class — remediation prose describing a command other than the one it belongs to (see seeds-3dkj). The category identified here turned out to be more general than the single bug that surfaced it. What a better bead would have said: when you find one instance of "guidance that does not match its command," sweep for the others before closing, because the pattern is shared user-facing text written next to one call site.
