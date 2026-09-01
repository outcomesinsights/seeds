---
id: seeds-ngez.1
title: "Harden the git test sandbox: enforce the single door, and close the HOME-based config paths"
status: resolved
type: decision
parent: seeds-ngez
created_at: 2026-08-26T22:08:55.449652+00:00
updated_at: 2026-08-31T21:35:01.470738+00:00
resolved_at: 2026-08-31T21:35:01.470730+00:00
resolution: "Shipped (bead seeds-3xs). Both decisions held. DECISION 1 (do not wholesale-mock git) was kept, and the reasoning proved out: the sandbox catches git doing things we did not predict, which a mock by definition cannot. The HOME-based config paths are closed as a category rather than one path — tests/githelpers.py sets GIT_CONFIG_GLOBAL=/dev/null, GIT_CONFIG_NOSYSTEM, HOME and XDG_CONFIG_HOME at the sandbox — and the single door is enforced by tests/test_git_single_door.py. Efficacy: none; the seed specified both gaps precisely enough to build from."
tags:
  - testing
  - git
  - isolation
  - mocking
  - enforcement
  - 2026-08-26
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Follow-on to the 2026-08-26 incident in the parent seed. The containment
shipped in 3919c00 works, but it leaves two gaps, and answering "should we
just mock git instead?" settles the shape of both.

DECISION 1: DO NOT WHOLESALE-MOCK THE GIT TESTS. @aguynamedryan asked whether these
tests could mock the git interaction rather than sandbox it. They should not,
and the reason is structural rather than stylistic: a mock encodes what we
PREDICT git does, and every bug in this family has been git doing something we
did not predict -
- GIT_DIR overriding cwd-based discovery entirely;
- core.bare making `git init` re-initialize an existing real repo as bare;
- GIT_AUTHOR_*/GIT_COMMITTER_* outranking config, so test commits were
  authored as the real user, but only under a pre-commit hook.
A mocked suite would have been green through all three. The third was caught
precisely BECAUSE a real commit ran and the author came back wrong. Mocking is
blind to exactly the bug class these tests exist to catch.

Worth recording that the pyramid ALREADY exists here and did not need
inventing: tests/test_gitstage.py mixes mocked-subprocess tests (the parse and
degradation paths - "git not installed", "rev-parse failed") with real-repo
tests, and after 3919c00 there are zero raw real-git calls outside
tests/githelpers.py. The line is in the right place. Mock what is about OUR
parsing; use real git for what is about GIT's behaviour. This decision is
about not moving that line, not about drawing it.

GAP 1: THE SINGLE DOOR IS A CONVENTION, NOT AN INVARIANT. tests/githelpers.py
is currently the only path to real git, but nothing enforces that. Two
previous agents independently wrote their OWN copy of _git/_git_init - that
duplication is precisely how one copy came to poison the real repo, and
deduplicating it was half of 3919c00. Nothing stops a third copy appearing in
the next bead. Fix: a test that scans tests/*.py and fails if any file other
than githelpers.py invokes real git. Cheap, and it converts today's
cleanliness into something that stays true.

Note the check must not trip on the legitimate mocked tests, which mention
["git", "diff"] inside a patched subprocess.run. So it should look for actual
invocation (subprocess.run/Popen/check_output with a git argv), not for the
string "git".

GAP 2: HOME IS STILL READABLE. git_env() points GIT_CONFIG_GLOBAL and
GIT_CONFIG_SYSTEM at os.devnull, which covers ~/.gitconfig. But git still
consults HOME for other things - include.path chains, init.templateDir,
credential helpers. Measured on titan 2026-08-26: neither include.path nor
init.templateDir is set globally here, so this is theoretical TODAY. It is two
lines to close the category rather than the instance, and the whole lesson of
the parent seed is that the instance is never the last one.

BOTH ARE SMALL. Neither changes the containment design; they harden it. The
alternative considered and rejected for gap 1 was a ruff lint rule, which
cannot express "except in this one file" cleanly enough to be worth it.


TRACKED AS: bead seeds-3xs (P2 task).


--- IMPLEMENTED (2026-08-26, commit 1cde6d2) ---

Both gaps closed as designed, and the enforcement check earned its keep
immediately: on its first run it flagged a bypass in the very test file that
shipped with the sandbox. test_host_global_config_is_not_readable called
subprocess.run directly - sandboxed, so harmless, but AROUND the door, which
is how a single door stops meaning anything. Rewritten to go through git(),
and made non-vacuous with a skip when the host has no global identity. It
locates the host config by READING the file rather than asking git, because
asking git unsandboxed is precisely the thing being forbidden.

Detector design, since the naive version does not work: the check walks the
AST for real call nodes rather than grepping for "git", because it must tell
INVOKING git from MENTIONING it. test_gitstage.py legitimately builds
subprocess.CompletedProcess(args=["git"], ...) and compares
args[:2] == ["git", "diff"] inside a patched subprocess.run; a grep would
flag both. Nine tests pin the detector on hand-built samples in both
directions - every process-starting entry point, the shell-string form, an
absolute /usr/bin/git, and the exact splat shape the old duplicated helper
used, against the three mention-only patterns that must not trip.

A second guard, test_githelpers_is_where_git_actually_runs, asserts the
allowlisted file DOES still invoke git - so if the door ever moves, the
allowlist fails loudly instead of silently permitting nothing.

668 passed, mypy strict and ruff clean, suite green under the pre-commit hook.
