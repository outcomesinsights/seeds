---
id: seeds-q0mg
title: '0.8 prep: over-engineering audit of the 0.7 tree, ~1,450 lines cuttable (33 ranked findings, 4 need rulings)'
status: captured
type: exploration
created_at: 2026-10-07T17:36:18.150919+00:00
updated_at: 2026-10-07T17:36:18.150919+00:00
tags:
  - 0.8-prep
  - audit
  - over-engineering
  - simplification
  - ponytail
---

## Context

A whole-repo over-engineering audit (ponytail-audit) run 2026-10-07 against the 0.7.0 branch at 1d442af (0.7.0a9). The scope was complexity only: dead code, stdlib/native replacements, duplicate helpers, yagni layers. Bugs, security and performance were out of scope.

Method: four read-only agents, one per slice: cli.py; convert/legacy/models; seedfile/check/store; and everything else plus scripts, deps, flake and hooks. Each `delete` was grepped across src, tests, scripts and docs, including string references. The lead session re-verified the biggest claims: conversion_audit.py has no references outside lint caches, EMPTY_TREE has none at all, and the legacy Seed helpers, read_seed, Store.delete and Store.all_tags are referenced only by tests.

RULED 2026-10-07: none of this lands on the 0.7.x line. Convert to beads AFTER the 0.7.x branch ships; all of it is 0.8.x prep. Line numbers below are as of 1d442af and will drift. Re-grep each one when it becomes a bead.

## Needs a ruling before it becomes a bead

- **Item 1, the differential harness.** It proves the 0.6 to 0.7 conversion repo by repo. Keep it until 0.7 is public and the fleet has converted, including Mark's repos, which were still on 0.6 as of 2026-10-06.
- **Item 14, `show --output-file`.** seeds-137 ended with "remove --output-file entirely?" and nobody ruled.
- **Item 20, the `seeds skills install` alias.** It is in README, CHANGELOG and 3 test files. The options are to keep it or to tombstone it like the other removed 0.7 commands.
- **Item 31, `report_collisions` / `report_orphans` in convert.py.** Their comment says those rows are "reported", so this may be a report that was meant to exist and doesn't, rather than dead code.

## Ranked findings (biggest cut first)

01. delete `scripts/differential_harness.py` (1888), `tests/test_differential_harness.py` (809) and the 3 `differential*` justfile recipes (justfile:108-142), about 2,700 lines. Replacement: git history. CONDITIONAL, see above. The bead that built it, seeds-4co.17, is closed.
02. delete `scripts/conversion_audit.py`, 651 lines. Replacement: nothing. It was a one-off for bead seeds-4co.15 (closed), nothing invokes it, and it imports the private `check._title_violation`.
03. reuse `seedfile._validate_for_write` (1331-1400) re-states the reader's rules. Replacement: in `render_seed_file`, round-trip through `parse_seed_file`. Keep asserts for a naive tz (`_encode_timestamp` silently localises it) and a newline inside a tag (the reader misses it). About 55 lines, medium.
04. delete legacy `Seed` helpers that only test_models.py uses: `generate_id` (models.py:78), `get_parent_id` (:360, the same as `seedfile.expected_parent`), `Seed.parent_id`, `.is_terminal`, `.has_been_edited` (live copies are at store.py:784/789), and `UNSET_TIMESTAMP` plus `__post_init__` (no src caller relies on the defaulting). About 50 lines plus their tests.
05. shrink `convert.union_records` (1152-1241). Replacement: one loop over the four `_pick` fields; body = `fork_body(...) if FORK else max(non-None bodies, key=len)` (max keeps the db body on a tie); tags = `list(dict.fromkeys(...))`. About 30 lines.
06. delete in candidates.py: `find_candidates(seeds_dir=)`, which its docstring calls "accepted and ignored" (drop the kwarg at cli.py:3533); the public `parse_lineage`/`malformed_lineage` wrappers (195-222), which only tests use, so point them at `_parse_lineage`; and the undocumented `"records"` key fallback (:316). About 30 lines.
07. stdlib `seedfile._BoundedMemo` (1110-1137, plus get/put at 1272-1281) is an LRU cache written out by hand. Replacement: `functools.lru_cache(maxsize=_MEMO_SIZE)` on a helper keyed by `json.dumps(options, sort_keys=True)`, which keeps `true` and `1` distinct and accepts lists, the stated reason for the custom class. About 25 lines.
08. reuse `convert._Half` (549-556) duplicates `models.Relationship`, and `_load_db` (694-706) copies one into the other field by field. Replacement: a frozen `Relationship` and `dataclasses.replace` in `_apply_renames`; `_edge_key(source, target, rel_type)` drops the dummy `_Half` in `_verify_edges` (1897). Also `_Side.origin` is set at 656/674/832 and never read, so `_Side` becomes `dict[str, Seed]`. About 37 lines.
09. native the `parse_since` try/except is written out 5 times (cli.py:1092, 1137, 2856, 2982, 3513). Replacement: one Click `callback=` that raises `click.BadParameter`. The exit code changes from 1 to 2; the tests only assert non-zero. About 22 lines.
10. reuse `jsonexport.read_corpus` and `check._load_store` (check.py:575-594) duplicate `Store.records()` (store.py:319-336). Replacement: `Store(dir).all()` with errors mapped to `ExportError`. `path.name[: -len(FILE_SUFFIX)]` appears at about 12 sites; use `removesuffix` or `store._id_of`. About 20 lines.
11. delete production methods only tests call: `seedfile.read_seed` (920), `Store.delete` (493), `Store.all_tags` (379). Inline `Store.invalidate` (286, one caller; its "every write calls this" docstring is false). About 20 lines.
12. shrink `beads.query_bead_ids` / `all_bead_ids` (70-169) repeat the which, run, json.loads, id-set steps. Replacement: one `_bd_json(seeds_dir, *args)` plus `_ids(payload)`. About 20 lines.
13. reuse the parent rule is written 3 times: `seedfile._build_record` (739), `_validate_for_write` (1349) and `check.check_record` (288, with remediation copied in `_PARSE_FIX`). Fold `check._chain` (399) into the one walk in `_check_parent` (354). About 20 lines, medium, because the cycle rule was deliberate.
14. delete `show --output-file` (cli.py:1293-1331) and its test (test_cli.py:3586). Replacement: plain `seeds show`. NEEDS RULING. About 17 lines.
15. delete `require_init` (cli.py:755-765), `Context.ensure_init` (159) and `import functools` (5). Nothing calls them. About 16 lines.
16. flake.nix: `apps` is redundant with `meta.mainProgram`, and the `inherit (...) python3Packages git ripgrep makeWrapper` block is copied 3 times. Replacement: `pkgs.callPackage mkSeeds { }`. About 22 lines.
17. reuse `check._as_renamed` (1429-1470) replays `Store.rename_prefix` (734-750). Replacement: one pure `renamed_record(...)` both call; the three `rewrite_id_refs` calls become a loop. About 15 lines, medium.
18. reuse `convert._legacy_table_counts` (734-758) plus the one-item `LEGACY_TABLES` open a second SQLite connection. Replacement: `LegacyDatabase.count_rows()`, since `list_questions` exists now. About 15 lines.
19. delete `convert.Normalization` / `NORMALIZATIONS` (180-245). Nothing reads them, only `__all__` and a docstring. Replacement: a comment block. About 15 lines, medium.
20. yagni the `seeds skills install` alias (cli.py:3380-3394, plus `_reinstall_option`). Replacement: a tombstone entry. NEEDS RULING. About 15 lines.
21. reuse "parse ISO timestamp, assume UTC" exists 4 times: glean.py:279 and :691, candidates.py:263, models.py:239. Replacement: one `parse_utc()` in models. `.replace("Z", "+00:00")` is unnecessary on Python 3.11 and later. About 15 lines.
22. shrink `gitstage.git_text` / `git_bytes` (73-107) are one function. Replacement: `_run_git(cwd, *args, text=, stdin=)`; build the 4 `DeletionPlan(...)` copies once or use `partial`. About 15 lines, medium.
23. native `scripts/check_git_config_sanity.py` `shared_config` (40-64) parses `.git` files and the gitdir layout by hand. Replacement: `git rev-parse --git-common-dir` plus `/config`. Unverified whether that works on a poisoned `core.bare=true` repo. About 15 lines, medium.
24. reuse `_clip` exists 3 times (check.py:947, glean.py:864, winnow.py:479), and the measurement regexes are duplicated (glean.py:390-406 against winnow.py:534-542, whose unit lists differ slightly). Replacement: one copy of each in textmatch.py, or `textwrap.shorten`. About 23 lines; check whether the unit-list drift is deliberate.
25. stdlib replace hand-built dicts and tallies. `asdict` replaces `winnow.report_as_dict.render` (731) and `candidates._finding_as_dict` (479). `Counter` replaces the tallies in `winnow._unresolved` (284), `prime.build_digest` (472), `convert._tally_vestigial` (728), the classification count (1994) and the doctor non-standard-type tally (cli.py:2441). About 26 lines.
26. stdlib `check._COMPARED_FIELDS` (1146-1159). Replacement: `dataclasses.fields(SeedRecord)` minus `id`, with `{"seed_type": "type"}` for the one label. A new field is then compared automatically. About 12 lines.
27. stdlib `legacy.first_difference` (435-446). Replacement: `len(os.path.commonprefix((a, b)))`. Also merge `check._first_difference` (929) with `_first_body_change` (1550), which are the same algorithm. About 22 lines.
28. shrink `seedfile._build_record` (686-764) repeats `_scalar` / assert / `[0]` for 6 keys. Replacement: a `_required(path, values, key)` helper. About 12 lines.
29. yagni the `idgen` min/max/prob params only ever get the `DEFAULT_*` constants (store.py:421, 692), and the "overridable via the seeds config table" comment is stale. Replacement: constants; `encode_base36` pad/trim becomes `rjust(n, "0")[-n:]`. About 12 lines.
30. shrink CLI copies. The list-output block appears 5 times (list/recent/search/ready/deferred), so add `_echo_records`. The "not found" handling is written out 4 times (show, history, ask, link) instead of calling `get_seed_or_exit`. The store guard appears 3 times (check/convert/export), so add `_seeds_dir_or_exit`. Prefix validation appears 2 times (init, rename_prefix). The body-flag option list appears 2 times (496/548). `STATUS_ICONS` is duplicated in prime.py:393, so keep one copy in models. `_uninitialized_error` has a redundant first branch. `click.Choice(SeedStatus)` (Click 8.2 and later) drops the `.value` lists, but check the `relates-to` spelling first. About 50 lines.
31. delete dead params and fields: `check_smells(now=)` and `del now` (check.py:656); `glean.auto_create(extra_tags=)` (780); `format_report(show_suppressed=)` (817); the glean `home=` kwargs, a second test seam beside `_home()`; `seedfile._Block.line` (525); `githistory.EMPTY_TREE` (43-46, which its own comment calls "Not used"); `prime.build_digest(limit_tag_clusters=)`; `SupersededScope` fields that only tests read; and convert.py's `report_collisions` / `report_orphans` (639-672), which NEED A RULING. About 30 lines.
32. yagni prefix logic has two layers: module `get_prefix` / `has_prefix_configured` / `write_prefix` (store.py:216-242) under `Store` methods that only pass the call through (272-282). Keep one layer. Also define `TERMINAL_STATUSES` once instead of 7 times (store.py:80, check.py:653, seedfile.py:767 and 1365, winnow.py:235, convert.py:1215, models.py:431). About 14 lines.
33. native hooks and deps. `.pre-commit-config.yaml` pulls a second ruff (ruff-pre-commit v0.15.13) beside the dev dep `ruff>=0.16.6`, and its `--fix` / `ruff-format` hooks rewrite files, against the justfile's fmt-check rule. Replacement: local `just fmt-check` plus `uv run ruff check` hooks. The `pre-commit` dev dep duplicates prek. The justfile `pre-commit: fmt-check` recipe has no invoker. About 10 lines, medium.

Smaller items seen but not ranked: `convert._ABBREVIATIONS` one-per-line (33 lines, could be `frozenset("...".split())`); the `_existing()` try/except copied 3 times in convert.py, plus a memo dict that could be `functools.cache`; `_set_detail` against `preview_ids`; convert.py writing `config.yaml` by hand instead of `store.write_prefix`; legacy `has_prefix_configured` plus `get_prefix` → one `configured_prefix()`; `ctx.ensure_object(Context)` redundant with `ensure=True`; the code-fence toggle written twice in seedfile.py (1497 and 1597), where markdown-it is already loaded; conflict-marker regexes defined twice (seedfile.py:1177, check.py:168), with seedfile missing the diff3 `|||||||` marker.

Not over-engineering, but false: seedfile.py:34-35 and store.py:197 say click is the only runtime dependency. mdformat and mdformat-gfm are pinned now.

Checked and kept: the hand-parsed YAML subset (no YAML dep, and the byte layout matters), the atomic write, the 0.7 tombstones, textmatch.py, history.py, trellis.py, claude_plugin.py, the `cat-file --batch` plumbing in githistory, and the single git door (nothing outside gitstage calls git).

## Totals

About 800 lines in src and config, plus 651 (conversion_audit.py), for roughly 1,450 lines now. About 4,150 if the differential harness also goes. Two dependencies can go: the `pre-commit` dev dep and the remote ruff-pre-commit hook repo.

Side note from a correctness angle, out of this audit's scope: convert.py's `_write_config` (around 2298) takes the prefix with `split("-")[0]`, which disagrees with `_split_id` for hyphenated prefixes. Route it to a normal review or a bug bead.
