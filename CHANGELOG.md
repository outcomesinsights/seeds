# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.6.0] - 2026-08-31

**This release is about failing loudly.** 0.5.0 stopped seeds destroying
deliberation silently; 0.6.0 stops it *losing* deliberation silently — and the
difference was found the hard way, by the project's first external bug report.

A user's sync had been broken for five weeks. An agent had written a seed type
the CLI does not accept directly into the JSONL, and the import aborted on that
line — so every record filed *below* it never reached the database, while every
record above it did. Nothing said so. `seeds doctor` reported healthy the entire
time, because its sync check compared file mtimes and never read the file. The
tool you run to ask "is my sync healthy?" was answering from a proxy that is
*anti-correlated* with this exact failure: a failed import leaves the JSONL
newer than the database, which is precisely the state it was calling clean.

Both halves are fixed. A record the import cannot read is now refused
**individually** and named — record number, id, failing field, reason — while
every other record lands, and the command exits non-zero so a script notices.
`doctor` no longer compares mtimes; it runs the same divergence check `sync`
does, so it is green exactly when `sync` would succeed rather than when a
timestamp happens to look right.

The type vocabulary that started it is open now. `seed_type` accepts any
string, `seeds update --type` fixes one, and `seeds retype` sweeps a typo across
the corpus. `SeedStatus` deliberately stays closed — status drives lifecycle
behaviour, so an unrecognised value there would break `ready`, `blocked` and the
resolve/defer/abandon transitions quietly rather than loudly.

### Breaking

- **Python 3.10 is no longer supported; the floor is 3.11.** 3.10 reaches
  end-of-life in October 2026, and seeds already required 3.11 in practice — it
  imports `enum.StrEnum`, so on 3.10 it had become an ImportError at startup for
  every command. ([6a70429](https://github.com/outcomesinsights/seeds/commit/6a7042910ff31c0f1b4983a5831199336b19fba2))
- **`seeds sync` refuses to flush** when it would change `.seeds/seeds.jsonl`
  while unrelated files are staged, rather than folding seed-database changes
  into whatever commit fires next. `--allow-mixed-stage` overrides.
  ([00ed416](https://github.com/outcomesinsights/seeds/commit/00ed4165ec26ce5edcfc22053e2ba119f886715e))
- **`seeds answer` refuses to overwrite a prior answer** instead of silently
  replacing it. ([89e6db0](https://github.com/outcomesinsights/seeds/commit/89e6db04590a19308f46ded9bc8594bcede20395))

### Upgrading

`seeds import` and `seeds sync` now **exit non-zero when any record was
refused**, where previously an unreadable record raised a traceback and stopped
the file. Scripts that treated a zero exit as "everything imported" were already
wrong — they just could not tell. If a sync starts reporting refusals, the
records it names have never been in your database; fix them in the JSONL and
re-run. `seeds doctor` now surfaces the same records before an import is run.

### Added

- Accept `seeds update` content from a file or stdin — `--content-file PATH` and
  `--content -` — so a long body no longer has to be quoted through argv
  ([d842efc](https://github.com/outcomesinsights/seeds/commit/d842efcaa02d7a991ece88a57305714186da68d4))
- `seeds retype --from X --to Y` bulk-remaps one seed type to another
  ([d21f7ba](https://github.com/outcomesinsights/seeds/commit/d21f7badc41aefe63db5551dc9a6f1cc5f18cb68))
- `seeds update --type` — a seed's type is no longer write-once
  ([c00bed0](https://github.com/outcomesinsights/seeds/commit/c00bed0b2ddc3ccdbaa9aff4da24c61693709dc2))
- The `seed_type` vocabulary accepts arbitrary strings
  ([15d3a6c](https://github.com/outcomesinsights/seeds/commit/15d3a6c3abf06469362f217490ac067e226dbdae))
- The bundled seeds-to-beads skill consults you before writing a bead;
  `--autonomous` opts out
  ([83e5f3c](https://github.com/outcomesinsights/seeds/commit/83e5f3c200f3c3f6e9ecbbf5fff4935a82acbb9f))
- `just changelog-coverage` gates a release on per-commit coverage rather
  than a count: every commit in the range must either render in the notes or
  match a deliberate skip rule in `cliff.toml`, and it names the ones that do
  neither. Replaces the count-based `changelog-audit`
  ([ac1cdc9](https://github.com/outcomesinsights/seeds/commit/ac1cdc9618f3258fdf1bc8fcbb6a4ee1fa6e6cad))

### Changed

- Python floor raised to 3.11 — see Breaking
  ([6a70429](https://github.com/outcomesinsights/seeds/commit/6a7042910ff31c0f1b4983a5831199336b19fba2))

### Fixed

- A malformed record is refused individually instead of aborting the import, so
  records below a bad line still land
  ([0c58123](https://github.com/outcomesinsights/seeds/commit/0c58123f006788a64daa9540d0a7d87748e8a265))
- `seeds doctor` agrees with `seeds sync` by construction, and names the record
  that breaks an import
  ([55bf114](https://github.com/outcomesinsights/seeds/commit/55bf1142d5e4a127060755bc0797c6501baff73d))
- `doctor` compares JSONL against the database instead of mtimes, and fails on
  divergence ([1600c37](https://github.com/outcomesinsights/seeds/commit/1600c372592dfd2a52b20c6d98d5ce6781033743))
- The divergence refusal no longer asks for a whole seed body through argv
  ([ccee855](https://github.com/outcomesinsights/seeds/commit/ccee8555fb2557b498b5d09779bfcc355e64a906))
- The divergence guard's guidance can now actually satisfy the guard
  ([54057b1](https://github.com/outcomesinsights/seeds/commit/54057b1546fa8b9c81b364cd97b3ab7823b86723))
- The content guard prints remediation for the command that raised it
  ([f6f010f](https://github.com/outcomesinsights/seeds/commit/f6f010f8e0eae581cb9ff6611e81483bd74c7cbf))
- A fresh clone is pointed at `seeds import` instead of being sent in a circle
  ([5589268](https://github.com/outcomesinsights/seeds/commit/5589268c02c7fd0045aeac25a8d1854bc02d0c29))
- Hyphenated queries search — FTS5 syntax characters are quoted
  ([46c63b8](https://github.com/outcomesinsights/seeds/commit/46c63b8883a7186b47474a03ceec9c56ece69159))
- `cliff.toml` no longer silently drops unhandled commit types
  ([e8320d2](https://github.com/outcomesinsights/seeds/commit/e8320d20c98d92a4bf413767d17f4732d79187f8))
- `cliff.toml` skips `docs(seeds…)` alongside `chore(seeds…)`, so edits to
  this repo's own seed database stop rendering as user documentation
  ([841a4dc](https://github.com/outcomesinsights/seeds/commit/841a4dc637f2e9cd9f95a43d0c34a1a149ee70c6))
- The release changelog uses an explicit tag range instead of
  `git-cliff --unreleased`, which dropped commits after a merge
  ([7cad77f](https://github.com/outcomesinsights/seeds/commit/7cad77f2bd4b6223ab52aa81042e487d30a614ee))
- Git test fixtures are sandboxed so they cannot poison the real repository
  ([3919c00](https://github.com/outcomesinsights/seeds/commit/3919c006760adbd72fdbccf40f73984acabaf096))
- The test sandbox has git, and two tests no longer assume a git checkout
  ([859aacd](https://github.com/outcomesinsights/seeds/commit/859aacd1882a7caaee4abb2001e98dd3efe8c300))

### Documentation

- Document the new content inputs and per-record import refusals; repair the
  changelog link references, which stopped at v0.3.3
  ([827a028](https://github.com/outcomesinsights/seeds/commit/827a0284d7b1f970d2d96a99daac310060fb70bf))
- Point the release checklist at `just bump-version`, which covers the two
  plugin manifests the old wording omitted
  ([161622b](https://github.com/outcomesinsights/seeds/commit/161622b9985998e4667e26b8c73746cf13351702))
- Split the global-CLI refresh by install method — `which seeds` decides
  between the nix profile and a `uv tool` install, since the nix profile
  precedes `~/.local/bin` on PATH and silently shadows the other
  ([260bc53](https://github.com/outcomesinsights/seeds/commit/260bc53c16f27e8fda73f48b70ed7f089224349e))
- Document `seeds import`, round-trip sync, and the fresh-clone path
  ([6336416](https://github.com/outcomesinsights/seeds/commit/6336416760a31d1af3138c8735643f2d46049c1c))
- Document the open type vocabulary, `update --type`, and `retype`
  ([a72ab29](https://github.com/outcomesinsights/seeds/commit/a72ab29fd1c41df645bc0f320e8db64ca8adc2a3))

## [0.5.0] - 2026-08-10

This release is about one thing: **seeds now refuses to destroy deliberation
rather than doing it silently.** Four commands that previously succeeded can
now exit non-zero — every one of them at a moment where the old behaviour lost
work without saying so. That is why the minor version moves.

The headline is `seeds sync`. It imports, then rewrote the JSONL wholesale from
the database **without ever reading the file it was about to overwrite**. So a
routine sync could erase deliberation that was on disk and never in any
database — no clock skew required. The clearest case: machine B appends and
pushes; machine A appends later without pulling; a human resolves the git
conflict *in B's favour*; A runs `sync`; the import correctly skips B's line
and the export then overwrites the file with A's version. B's text is gone and
the human's explicit resolution is reverted, reported as `1 skipped` — which is
what every *unchanged* seed prints. The export now reads the file first and
refuses on divergence.

Timestamps were the second half. Records carried their `updated_at` verbatim
from the file, so a future-dated record became **permanently** authoritative:
every later local edit stamps `now`, which is *earlier*, so the poisoned record
out-ranked real work forever and each import destroyed whatever had been typed
since. Records dated beyond a small skew tolerance are now refused outright, and
a timezone-naive timestamp no longer aborts an import mid-file.

`seeds update -c` got the same treatment at a smaller scale: one character from
`-a`, it replaced a seed's whole body with no warning. It now refuses once a
seed has accumulated deliberation, unless you mean it.

### Breaking

- **`seeds sync` / `sync --flush-only` refuse to overwrite divergent JSONL.** Pass `--allow-divergence` to discard the on-disk content deliberately ([bfb518e](https://github.com/outcomesinsights/seeds/commit/bfb518ec98804e9af3d197ebef601fc985ba64cf))
- **`seeds import` refuses records dated more than 5 minutes in the future.** They are reported, and the database is left unchanged ([0a867dd](https://github.com/outcomesinsights/seeds/commit/0a867dd01ef44d43602b94353497d66b5db607e7))
- **`seeds update -c` refuses on a seed that has been edited.** Use `-a` to append, or `--replace` to discard on purpose. Note `--replace` does not erase anything — the old body survives in git history ([03f3af3](https://github.com/outcomesinsights/seeds/commit/03f3af324be5acbef88200edad0dc5b5e8102327))
- **`seeds create` / `update` now reject unknown base36 ID references.** Hash-shaped references like `seeds-zq4x` were previously invisible to the hallucinated-ID check, which is the scheme every new ID uses. `--allow-unknown-refs` still overrides ([fd778ed](https://github.com/outcomesinsights/seeds/commit/fd778edd3632d058ef3a4556aa3e20c9eaab7b8a))

### Added

- `--add-tag` / `--remove-tag` on `seeds update`, both repeatable. Removing a tag a seed does not carry is a silent no-op reporting the count, so a typo shows as "0 removed" rather than failing mid-batch. Wholesale `--tags` is unchanged ([d7d678b](https://github.com/outcomesinsights/seeds/commit/d7d678b3d41751f19d5268ae9f34d3b03ea08c2c))

### Fixed

- Bead IDs count as known references in seed bodies. Beads share the `seeds-` prefix, so every legitimate bead citation previously failed seed creation and had to be worked around with `--allow-unknown-refs` ([e2f7b64](https://github.com/outcomesinsights/seeds/commit/e2f7b6472feac64ee0df4471d6c94421bddaf075))

### Changed

- `seeds suggest --json` emits compact JSON. The flag's purpose is agent piping, where indentation is tokens the model pays for — 21% smaller on a live query. Pipe through `jq` to read it ([c20d7db](https://github.com/outcomesinsights/seeds/commit/c20d7db32e5a84e093cad24e9f34265c83feff0f))

## [0.4.0] - 2026-07-27

This release makes seeds installable with **Nix**, and finishes the base36 ID
transition that 0.3.5 began by removing the one command that could undo it.

The minor version moves for the first time since 0.3.0. The 0.x convention
here is that features ship as patch bumps, so `0.4.0` is a deliberate signal
rather than a routine increment: a command has been **removed**, and anyone
scripting against `seeds migrate-ids` will break.

`flake.nix` means `nix run github:outcomesinsights/seeds` works with no
install at all, and Nix users can pin seeds as a flake input instead of
hand-writing a derivation. It also exposes an `overlays.default` for
home-manager configs, a `devShells.default` giving contributors a pinned
Python + uv + ruff toolchain, and a `checks.default` that runs the test
suite. Tests deliberately live in `checks` rather than gating the package,
so consumers building from source don't pay for a full pytest run. A CI job
builds the flake on every push — an untested flake is a broken promise.

The headline fix is a data-integrity bug in `rename-prefix`. It decided which
IDs to rename with a numeric-only shape test written when every ID was
sequential. Base36 includes `0-9`, so a hash like `seeds-060` parsed as a
number and was renamed while `seeds-k3n7` was skipped — same scheme, opposite
outcome, decided by the random content of the hash. On a real database that
left a **split-prefix state**: some seeds renamed, hash-ID seeds stranded
under the old prefix, while the configured prefix reported the new one. Both
schemes are now renamed, and body references were taught base36 too.

**Breaking:** `seeds migrate-ids` is gone, with no deprecation shim. It
migrated hash IDs *to* sequential — backwards since 0.3.5 made base36 hash
IDs the standard. Because it detected work by testing whether an ID parsed
as a number, every base36 ID read as un-migrated, and a single one was enough
to renumber an **entire** database from 1. The migration was one-time, that
transition has concluded, and the command could now only do harm.

### Added

- Add flake so seeds is installable via Nix ([fa8dbb8](https://github.com/outcomesinsights/seeds/commit/fa8dbb872ed69bb177d523ba7d66634e110b087d))

### Fixed

- Rename-prefix must rename base36 hash IDs, not just numeric ones ([16b814d](https://github.com/outcomesinsights/seeds/commit/16b814d5bdcbde5592e894e59c181376020e5901))
- Drop x86_64-darwin, which nixpkgs 26.11 removed ([86790ae](https://github.com/outcomesinsights/seeds/commit/86790aee13806184dad6ff7a2f4f21ee4501eedd))

### Removed

- **Breaking:** remove migrate-ids and migrate_to_sequential_ids ([5cab711](https://github.com/outcomesinsights/seeds/commit/5cab7115832e2c100b458ea152aef9f0d8b8e75c))

### Tooling

- Add nix job so the flake can't silently rot ([1426a9f](https://github.com/outcomesinsights/seeds/commit/1426a9f5e173e90067043475f82130e7906f9232))
- Don't let `--all-systems` attempt cross-arch builds ([70151c7](https://github.com/outcomesinsights/seeds/commit/70151c74e078eaff1dc8ffc3496f45d65ade4587))

## [0.3.5] - 2026-07-17

This release changes how new seed IDs are minted: from a sequential counter
(`seeds-1`, `seeds-2`, …) to short, collision-resistant **base36 hash IDs**
(`seeds-k3n`), adopted whole-cloth from beads. The sequential scheme derived
each next number by scanning the local store, so the same git-backed repo
worked from two machines could mint the same ID on each and collide when the
JSONL merged; hash IDs need no shared counter, so that whole class of
collision is gone. Existing IDs are **grandfathered** — nothing is renumbered
and there is no migration. Suffix length scales with store size (3 characters
in a fresh store, 4 once it grows), keeping IDs as short and typeable as the
sequential ones they replace.

### Added

- Switch next_id() to base36 hash IDs (seeds-mlj) ([5a8346a](https://github.com/outcomesinsights/seeds/commit/5a8346a3587cd673e87ff58b0e7237e09a52e9e4))
- Add base36 hash-ID generator module ([9e5ca96](https://github.com/outcomesinsights/seeds/commit/9e5ca9669229016cde716fdcf6ed7001e2860dd2))

### Fixed

- Recover_prefix_from_id handles base36 hash IDs (fresh-clone bootstrap) ([ca89711](https://github.com/outcomesinsights/seeds/commit/ca89711b4eaefcc29ac2d7c057137e76beb0a25a))

## [0.3.4] - 2026-07-16

This release adds a new output mode: turning a matured seed into a *trellis*.

`seeds trellis <id> --to <file> --as "<principle>"` distills a resolved seed's
deliberation into one crisp, bounded principle and writes it — with a two-way
provenance link — into durable, always-on project context such as `CLAUDE.md`
or `README`, then resolves the seed. A trellis is a load-bearing principle
you want every future session steered by; it lives in the context the agent
runtime injects each session, not in anything seeds surfaces internally. A
companion `seeds:trellis` skill supplies the language judgment — distilling the
one-line principle and advising the target file — and fires when you say
"promote this" or "make this a trellis". The verb's bookkeeping stays
deterministic (a provenance bullet under a `## Principles` section, a
`trellis` tag, and resolution), and README and CLAUDE.md explain when to
reach for it.

This release also **drops Python 3.9** (end-of-life; `requires-python` is now
`>=3.10`) and refreshes the dev toolchain — mypy 2.3, pytest 9.1, ruff 0.15.22,
and pre-commit 4.6.

## [0.3.3] - 2026-06-24

This release rounds out the seeds↔beads workflow and makes JSONL import a
first-class, round-trippable operation.

On the workflow side, the bundled skills now carry intent in both directions.
`seeds-to-beads` records the *why* behind each bead — locked decisions and their
rationale, verbatim stakeholder voice on subjective calls, and seed lineage —
and suggests a short efficacy note to capture when the work is done. A new
`resolve-seeds-from-beads` skill closes the loop: after an implementation
session it reconciles what actually shipped back into the originating seeds,
captures that efficacy note, and resolves them.

On the data side, `seeds import` lands with last-write-wins upsert semantics, a
fresh-clone bootstrap, and prefix recovery, so a seeds database can be rebuilt
from its JSONL export and synced round-trip without drift.

### Added

- **`seeds import [PATH|-]` with round-trip `seeds sync`.** Import seeds from a
  JSONL file or stdin; export and re-import are now lossless, enabling
  backup/restore and cross-clone sync.
- **Fresh-clone bootstrap + prefix recovery on import.** A freshly cloned repo
  with only its JSONL export can reconstruct a working database, recovering the
  project's seed-ID prefix.
- **Last-write-wins upsert for import.** Re-importing reconciles by `updated_at`
  and reports an `ImportResult` summary instead of duplicating or clobbering.
- **Executor intent in the `seeds-to-beads` skill.** Converted beads now record
  locked decisions + their rationale, verbatim stakeholder voice, and seed
  lineage — separating motivation from constraints.
- **Efficacy note suggested at seed resolution.** `seeds-to-beads` now proposes
  a short qualitative note (tweaking needed? planning-miss vs inherent unknown?)
  to capture when the originating seed is resolved.
- **New `resolve-seeds-from-beads` skill.** The symmetric bookend to
  `seeds-to-beads`: reconcile deliberation against what shipped, capture the
  efficacy note, and resolve the seeds.

### Documentation

- Added the intent-debt investigation and feedback-response notes under `docs/`.

### Tooling

- Beads now exports `issues.jsonl` on commit via a hook.
- Relocked ruff (0.15.14 → 0.15.16); raised the requirement floor to >=0.15.15.

## [0.3.2] - 2026-06-04

A correctness release for the Claude Code skills installer. `seeds skills
install` now guarantees the plugin ends up *enabled*, so the bundled `seeds:*`
skills actually load in new Claude Code sessions — previously the plugin could
install but sit disabled, silently contributing nothing. Clean package builds
are restored, and the version is now single-sourced so the CLI and the plugin
manifests can no longer drift apart.

### Fixed

- **`seeds skills install` now enables the plugin.** The command registered the
  marketplace and installed the plugin but never enabled it, so it could remain
  `disabled` in `~/.claude/settings.json` and load none of its skills. It now
  runs `claude plugin enable` on every install/update. A new `--reinstall`
  (alias `--upgrade`) flag refreshes the marketplace from source and replaces a
  stale cached copy after the seeds CLI itself is upgraded.
- **Clean wheel builds.** A redundant hatchling `force-include` re-mapped the
  bundled plugin files to wheel paths already provided by `packages`, so any
  build from a clean cache failed with a "same path" collision. Removing it
  fixes `uv build` / `uv tool install`.
- **Beads pre-commit hook.** Set `BD_GIT_HOOK=1` in the pre-commit entry to
  avoid a `.git/index.lock` race during beads' auto-export.

### Tooling

- **Single-sourced the package version.** `pyproject.toml` now derives the
  version from `src/seeds/__init__.py` (hatchling dynamic version); the two
  plugin manifests are kept in lockstep by `just bump-version`, guarded by a
  test that fails the build on drift. Previously the version lived in four
  hand-edited places and had already drifted (plugin manifests at 0.2.0 while
  the CLI was 0.3.1).

## [0.3.1] - 2026-05-27

First Claude Code skills shipped with seeds. The new `seeds skills install`
command registers a bundled local marketplace and installs the `seeds` plugin
under the `seeds:*` namespace (mirroring the `beads:*` pattern). Two
prompt-macro skills ship in this release; see `seeds-152` and its sub-seeds in
the seed database for the deliberation that produced them.

### Added

- **`seeds skills install`** — registers the bundled Claude Code plugin
  marketplace and installs (or updates) the `seeds` plugin under the user
  scope. Idempotent; safe to re-run after `uv tool upgrade seeds`.
- **`seeds:feedback` skill** — prompt-macro that frames the next user message
  as feedback on the agent's prior turn, then has the agent invite further
  questions, comments, or criticisms exactly once. Per the deliberation that
  produced it, the closer's value comes from being user-initiated; the skill
  explicitly scopes the invitation to the single reply being generated rather
  than installing it as ongoing agent behavior.
- **`seeds:seeds-to-beads` skill** — prompt-macro for converting deliberated
  seeds into a set of beads suitable for execution by a Sonnet-based agent.
  Encodes principles for separating actionable scope from context, embedding
  content templates in bead descriptions, writing mechanical acceptance
  criteria, and setting explicit dependencies.
- **Claude Code plugin tree** under `src/seeds/plugin/` — `seeds-marketplace`
  + `seeds` plugin manifests for local distribution. Bundled with the Python
  package via Hatchling's `force-include`.

### Documentation

- README section describing the Claude Code skills and the install command.

## [0.3.0] - 2026-05-18

Discovery and dedup primitives aimed at the recurring transcript-incorporation
workflow (see `seeds-142` in the seed database for the use-case write-up).

### Added

- **`seeds prime` digest** — appends counts, recently-updated seeds, active
  exploration, open questions, and top tag clusters after the static workflow
  text. Bodies are intentionally omitted; agents `seeds show <id>` for detail.
  Flags: `--no-digest`, `--digest-limit=N`.
- **`seeds suggest "<text>"`** — natural-language dedup query. Ranks existing
  seeds by FTS5 BM25 over title/content/tags/resolution, with multiplicative
  tag-overlap and recency boosts and a dynamic noise floor (drops hits below
  half the top score). Includes resolved/abandoned by default — the question
  is "does this idea exist in our deliberation history?", not "what can I edit
  right now". Flags: `--limit=N`, `--open-only`, `--json`.
- **`seeds list --since=<date>` / `--sort=updated|created`** — surfaces "what
  changed since X" as a first-class CLI primitive instead of forcing agents to
  derive it from `updated_at` timestamps inside seed bodies. Accepts ISO dates
  (`2026-05-08`), relative shorthand (`7d`, `2w`, `3m`, `1y`), and
  `today`/`yesterday`.
- **`seeds recent`** — thin alias for `seeds list --since=7d --sort=updated`.
- **Cross-reference validation on `seeds create` / `seeds update`** —
  rejects bodies that reference unknown `<prefix>-N` IDs (catches the
  hallucinated-cross-reference failure mode). Pass `--allow-unknown-refs` to
  override.

### Changed

- `seeds prime` command help reorganised: `suggest`, `search`, `recent` now
  sit alongside `ready`/`questions`/`deferred`/`blocked` in "Finding Work".

### Tooling

- Pre-push hook wired via pre-commit framework: runs mypy, ruff check, ruff
  format --check, pytest, plus beads pre-push. Matches the GitHub Actions
  lint+test jobs so CI on remote becomes the last line of defense rather
  than the first.
- ruff-pre-commit pin bumped v0.4.0 → v0.15.13 to match the local `uv` ruff
  version (the older pin disagreed with current isort defaults).
- Dev deps migrated from the deprecated `[tool.uv] dev-dependencies` field
  to PEP 735 `[dependency-groups] dev`.
- 359 tests (was 300).

## [0.2.1] - 2026-05-14

Configurable project prefix for seed IDs and supporting `rename-prefix`
improvements. This version was bumped in code but not tagged as a GitHub
release; its features shipped to users as part of v0.3.0.

### Added

- **Configurable project prefix** (`seeds-5at`) — `seeds init --prefix` and
  `seeds rename-prefix <new>` to change the prefix used on seed IDs after
  the fact. `seeds prefix` prints the current value.
- **`seeds rename-prefix --dry-run`** (`seeds-d7o`) — preview ID renames
  and body-reference rewrites without writing.
- **Body-reference rewriting** during `rename-prefix` — IDs mentioned inside
  seed titles/content/resolution are updated alongside the structural rename.
  Use `--no-rewrite-bodies` to skip.

### Documentation

- Added `docs/working-with-seeds.md` — primer + blog workflow.
- Clarified the design-database protection rule in `CLAUDE.md`.

## [0.2.0] - 2026-04-28

### Added

- **Typed relationships** between seeds (Phases 1 + 2): infrastructure +
  CLI/export/web wiring.
- **Sequential IDs** replacing random hashes, with migration of existing
  seeds.
- **Resolution field** to capture what happened when a seed is resolved.
- **Full-text search (FTS5)** across seeds and questions.

### Removed

- Deprecated `Question` / `QuestionStatus` and legacy DB columns.

### Tooling

- ruff lint cleanup, pre-commit hook wiring, beads hook shims to v0.61.0.

### Dependencies

- `click>=8.1.8`
- `flask>=3.1.3`

## [0.1.0] - 2026-02-27

Initial public beta release.

### Added

- **Seed lifecycle**: captured → exploring → resolved/abandoned/deferred
- **Quick capture**: `seeds jot` for minimal-friction idea capture
- **Hierarchical seeds**: parent/child organization with dotted IDs (e.g., `seed-a1b2.1`)
- **Blocking semantics**: seeds with unresolved children cannot be resolved
- **Attached questions**: first-class question objects with open/answered/deferred lifecycle
- **Tagging**: comma-separated tags with filtering support
- **Relationships**: bidirectional `seeds link` for loose coupling between seeds
- **JSONL export**: git-trackable export via `seeds sync --flush-only`
- **AI context**: `seeds prime` command for agent workflow injection
- **Navigation commands**: `seeds ready`, `seeds blocked`, `seeds deferred`, `seeds questions`
- **Experimental web UI**: `seeds serve` for read-only browsing of seeds and questions
- **Doctor command**: `seeds doctor` for installation health checks

[Unreleased]: https://github.com/outcomesinsights/seeds/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/outcomesinsights/seeds/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/outcomesinsights/seeds/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/outcomesinsights/seeds/compare/v0.3.5...v0.4.0
[0.3.5]: https://github.com/outcomesinsights/seeds/compare/v0.3.4...v0.3.5
[0.3.4]: https://github.com/outcomesinsights/seeds/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/outcomesinsights/seeds/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/outcomesinsights/seeds/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/outcomesinsights/seeds/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/outcomesinsights/seeds/compare/v0.2.0...v0.3.0
[0.2.1]: https://github.com/outcomesinsights/seeds/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/outcomesinsights/seeds/releases/tag/v0.2.0
[0.1.0]: https://github.com/outcomesinsights/seeds/releases/tag/v0.1.0
