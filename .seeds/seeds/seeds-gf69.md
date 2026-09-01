---
id: seeds-gf69
title: Should seeds ship a flake.nix so it can be installed declaratively via Nix?
status: resolved
type: question
created_at: 2026-07-26T16:42:23.232213+00:00
updated_at: 2026-08-31T20:02:48.809848+00:00
resolved_at: 2026-07-27T15:29:14.521449+00:00
resolution: "Yes — shipped in v0.4.0 (2026-07-27), including the home-manager half that the initial consultation advised against.\n\n## What shipped\n\n- **seeds-0y4** — `flake.nix` with `packages.default`, `apps.default`, `overlays.default`, `checks.default`, `devShells.default`. Version parsed from `src/seeds/__init__.py`, so releases need no flake edit (verified: the 0.3.5 -> 0.3.6 -> 0.4.0 bumps all propagated with zero manual changes).\n- **seeds-80g** — `nix` job in CI.\n- **seeds-808** — dropped `x86_64-darwin` after nixpkgs 26.11 removed it.\n- **hm-0jz** — home-manager now consumes `seeds.overlays.default`; `packages/seeds.nix` deleted. `seeds --version` on titan is 0.4.0 from `/nix/store/...-seeds-0.4.0/bin/seeds`, `flake.lock` pinned to the v0.4.0 rev.\n\nTwo unrelated bugs surfaced by the work, both fixed: **seeds-skc** (rename-prefix skipped base36 hash IDs, leaving split-prefix databases) and **seeds-28l** (migrate-ids renumbered an entire database if one base36 ID existed).\n\nThe single-source-of-truth goal is genuinely met: the runtime dep list and `pythonRelaxDeps` now live beside `pyproject.toml` instead of in a different repo with nothing enforcing agreement.\n\n## Efficacy note\n\n**Tweaking needed: minor-to-moderate.** Three planning misses, one inherent unknown.\n\n1. **Planning miss — a self-contradictory acceptance criterion.** seeds-808 required `grep -q 'x86_64-darwin' flake.nix` to find nothing, while the ruling simultaneously required a comment explaining the removal. Any useful comment contains the string. The executing agent correctly refused to satisfy it literally and verified the intent instead (zero *non-comment* occurrences + `nix flake show`). A better bead would have written the criterion as \"no non-comment occurrences,\" or not tried to express 'absent from the systems list' via grep at all.\n\n2. **Planning miss — the removal audit missed a file type.** hm-0jz's safety audit swept `*.nix` and `*.md` for references to the deleted derivation, but not the `Justfile` — whose `update-seeds` recipe hand-rewrote `version` and `hash` inside that very file. It would have broken on next use. Lesson: when deleting a file, grep for its *path* across ALL file types, not just the language's own extension.\n\n3. **Planning miss — the same class of bug wasn't swept for.** seeds-skc fixed one numeric-only ID shape test. Only a later prompted audit found `migrate-ids` carrying the identical assumption (seeds-28l), which was strictly worse — it renumbered whole databases. A better bead would have said: after fixing a shape-assumption bug, grep for every other site making the same assumption before closing.\n\n4. **Inherent unknown — local nix verification did not predict CI.** seeds-808 upgraded CI to `nix flake check --all-systems` and verified it green on titan. It then failed on the GitHub runner with \"platform mismatch\" building `checks.aarch64-linux`. Cause: titan runs nix 2.24.11, which silently skips foreign systems; the installer action ships a newer nix that attempts them. This was not catchable by a better bead — only by running it. Now encoded as a warning comment in `ci.yml`, and the job splits into `--all-systems --no-build` (evaluation coverage) plus a bare `flake check` (native build + tests).\n\n**The deliberation itself was worth more than the beads.** The consulted nix specialist recommended shipping the flake but NOT rewiring home-manager, pricing that half at \"~2 minutes per release.\" Ryan overrode it, and the override was right: the benefit was never minutes saved, it was that the dependency list lived in a different repo from `pyproject.toml` with nothing enforcing agreement. Recording the specialist's reasoning AND the override verbatim in hm-0jz is what let a Sonnet executor implement the half its own source recommended against.\n\n## Follow-on left open\n\n- **seeds-6hj5** (concern) — hallucinated-ID validation can't catch base36 hash refs, because a hallucinated hash and ordinary prose are shape-identical. Pre-existing, not caused by this work, but sharpened by it.\n- `~/.claude/plugins/known_marketplaces.json` still holds the pre-v0.4.0 store path; it reconciles from `settings.json` on the next Claude Code session. The old path is still GC-rooted by home-manager generations 170-176, so there is no immediate hazard.\n- boost and molt stay on the old seeds until the home-manager repo is pushed and switched on each."
tags:
  - nix
  - packaging
  - distribution
  - installation
relationships:
  - target_id: seeds-95
    rel_type: relates-to
    created_at: 2026-07-26T16:53:26.154134+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Raw thought (@aguynamedryan): "should we have some sort of nix flake in here to help with installation via nix? I do not even really know what it is I am asking." Part of this seed is clarifying the actual question.

A Nix flake (a flake.nix file at the repo root) is a standardized, reproducible way to package a project so the Nix package manager can build/run/install it. For a Python CLI like seeds it would expose a buildable package plus a runnable app. Two distinct value props:

1. Declarative install for @aguynamedryan own setup. @aguynamedryan manages tools via home-manager (~/.config/home-manager). Today seeds is installed imperatively per-machine via `uv tool install .`. A flake would let him add seeds as a flake input and have it installed declaratively, version-pinned, and reproducible across all hosts.

2. A distribution channel for public Nix users. Once seeds is public, a flake enables `nix run github:outcomesinsights/seeds` and `nix profile install github:outcomesinsights/seeds` for anyone on Nix — a first-class install method alongside pip/PyPI (see seeds-95) and git-clone.

Cost / open questions:
- Packaging a uv-managed Python CLI for Nix takes care. Options: nixpkgs buildPythonApplication, or the uv2nix / pyproject.nix toolchain. The dependency list must stay in sync with pyproject.toml (ongoing maintenance burden).
- Worth doing before the public release, or a nice-to-have after? Sibling of the PyPI-vs-GitHub distribution decision in seeds-95.
- Consult Hammond (nix specialist) on how cleanly this drops into @aguynamedryan home-manager config.

Not a decision yet — capturing the question so it can grow.

---

## Correction to two premises above (verified 2026-07-26)

The framing above was written without checking the home-manager config. Two of its premises are factually wrong:

1. **"Today seeds is installed imperatively per-host via `uv tool install .`"** — not true. seeds is ALREADY nix-packaged and installed declaratively on all three hosts. An earlier agent session added `~/.config/home-manager/packages/seeds.nix` (commit `5201ccd feat(seeds): nix-package the seeds CLI`), a 48-line `buildPythonApplication` over `fetchFromGitHub` pinned to `rev = "v${version}"`, consumed at `modules/packages.nix:139` via `callPackage`. That module is imported from the shared `home.nix`, so boost + molt + titan all get it. Verified on titan: `which seeds` -> `/home/ryan/.nix-profile/bin/seeds` -> `/nix/store/azymac...-seeds-0.3.5/bin/seeds`.
2. **"Repo is currently private, being prepared for public release"** — the repo is already PUBLIC (`gh repo view outcomesinsights/seeds` -> `isPrivate: false`). So the "before or after public release?" sequencing question is moot.

Payoff #1 as originally stated is therefore already fully delivered. What remains genuinely open is only payoff #2 (public distribution) and the devShell.

## Hammond's assessment (nix specialist, consulted 2026-07-26)

**Bottom line: do it later, low priority, public-facing only. Do NOT restructure home-manager around it.**

Strongest single reason: payoff #1 is already 100% delivered by `packages/seeds.nix`, so a flake buys @aguynamedryan personally nothing — and consuming it would be *net-negative*.

### Why consuming it would be net-negative

`modules/claude-code.nix:10` pulls the same derivation purely for its `.src` attribute and uses `"${seedsPkg.src}/src/seeds/plugin"` as the Claude Code plugin marketplace path (`claude-code.nix:635`). `fetchFromGitHub` is a fixed-output derivation, so that store path is **byte-identical across boost/molt/titan** — which ended a long-running `settings.json` churn problem (Claude Code normalizes marketplace paths to absolute and does not expand `~`/`$HOME`). Switching to `inputs.seeds.packages.${system}.default` would produce a different store path and rewrite that hard-won marketplace path. One-time churn, but pointless churn.

Also: it would be the **first flake-input-as-package** in the config. All five existing inputs (nix-darwin, home-manager, nixvim, nix-index-database, sops-nix) are consumed as *modules*; there are zero occurrences of `extraSpecialArgs`/`specialArgs` anywhere. Wiring a package input properly would mean threading `inputs` through `mkHome`/`mkDarwin` for the first time. (Cheap escape hatch if ever wanted: `flake.nix` already has an `overlays = [ ];` list in scope, so `overlays.default` from a seeds flake would be a ~4-line change — but it would only replace a working `callPackage` with a working overlay.)

### Payoff #2, not oversold

Realistic install-channel share for a niche Python CLI: `uv tool install`/`uvx`/`pipx` = essentially everyone; pip = long tail; Nix flake = a small vocal minority who would otherwise just `uv tool install` anyway. A flake does not meaningfully expand the audience — Nix users aren't blocked today.

What it genuinely provides:
- `nix run github:outcomesinsights/seeds -- jot "..."` — zero-install trial. One good README line.
- A copy-pasteable `inputs.seeds.url` so other people don't each rewrite the derivation.
- `nix develop` — pinned Python + uv + ruff + mypy shell. **Arguably the highest-value output** for a repo we want contributable.

What it does NOT provide: discoverability. Nobody browses flakes. Real Nix-ecosystem reach would mean upstreaming to nixpkgs (`pkgs/by-name/se/seeds/package.nix`) — but that's a PR review cycle plus an ongoing maintainer obligation, premature at v0.3.x with a fast release cadence. Don't.

### Mechanics: `buildPythonApplication`, not uv2nix — not a close call

uv2nix/pyproject.nix exists for large dep trees whose transitive deps aren't in nixpkgs. seeds has **two** runtime deps (click, flask), both first-class nixpkgs packages. Adopting uv2nix would add three flake inputs plus a `follows` dance and would track uv's lock format (so it breaks on uv releases). Wildly disproportionate. `uv.lock` has 34 entries but the great majority are dev-only; the real runtime closure is click + flask + werkzeug/jinja2/itsdangerous/blinker/markupsafe, all resolved automatically via `propagatedBuildInputs`.

Three worries, all resolved:
- **hatchling?** Non-issue, three lines, already proven: `pyproject = true; build-system = [ python3Packages.hatchling ];`
- **Dynamic hatch version?** Non-issue — hatchling reads `src/seeds/__init__.py` at build time; nix never touches it. Only cosmetic risk is the hand-declared nix `version` drifting from `__version__`. A repo-local flake can close that outright by parsing `__init__.py` with `builtins.readFile` + `builtins.match`, making per-release maintenance literally zero.
- **`src/seeds/plugin/` data files?** Non-issue — verified empirically in the built store output, not theorized. All six plugin files including the dotfile dirs (`.claude-plugin/marketplace.json`, `claude-plugin/.claude-plugin/plugin.json`, four `skills/*/SKILL.md`) are present. `[tool.hatch.build.targets.wheel] packages = ["src/seeds"]` sweeps them into the wheel and nix just installs the wheel. No `postInstall`, no force-include. The pyproject warning about force-include breaking the build is irrelevant to Nix, which never adds one.

The one real recurring wrinkle: `pythonRelaxDeps = [ "flask" ]` — nixpkgs ships flask 3.1.2 against our `>=3.1.3` floor. This recurs whenever a declared floor outruns nixpkgs-unstable. One-line fix each time. So honest maintenance is "not zero, but occasional and trivial."

### Sequencing: nothing blocks, nothing is blocked

- Public release: already done, not a gate.
- **PyPI naming (seeds-95) is completely orthogonal — do not couple them.** A repo-local flake uses `src = ./.;` and never touches PyPI. `fetchFromGitHub` is entirely idiomatic (often preferred, since tests come along with the source).
- **The one real prerequisite**: if we add a flake, add a `nix build` job to `.github/workflows/ci.yml`. A flake that silently rots is worse than no flake — it becomes a broken promise in the README.

### Effort

| Item | Cost |
|---|---|
| `flake.nix` (packages/apps/overlays/devShells) | 45-60 min — derivation already written and proven; mostly `forAllSystems` boilerplate |
| CI `nix build` job | 10-15 min |
| README `nix run` section | 5 min |
| Per-release maintenance | ~0 with the `readFile` version trick; occasional 1-line `pythonRelaxDeps` fix |
| Switching @aguynamedryan's hosts to consume it | **Don't.** Keep `packages/seeds.nix`. |

One deliberate difference Hammond recommends between a repo-local flake and the existing `packages/seeds.nix`: that file sets `doCheck = false` (correct — it just wants a binary on the hosts). A repo-local flake gets `tests/` for free via `src = ./.;`, so it SHOULD run them via `pytestCheckHook`. Small genuine quality gain for the artifact strangers consume.

### Hammond's closing note

"If you'd rather not spend the hour: that is a completely defensible call. The flake's honest value is one README line plus a contributor devShell. Neither is load-bearing for a tool whose realistic install path is `uv tool install`. This belongs in a nice-to-have polish bucket, **well below the unresolved PyPI naming question** — which does gate the primary install channel and is worth more attention." (See seeds-95.)

---

## Counter to Hammond's weighting — direction now leans YES (2026-07-26)

@aguynamedryan pushed back on "don't rewire home-manager": *"it seems like I'd have a single change to home-manager and then it would be able to track seeds from seeds' flake just like everyone else — that sounds like a Good Thing and worth the cost of a one-time change across hosts."*

That's right, and on review Hammond's cost/benefit weighting was off. His mechanics were sound; his pricing of the payoff was not. Verified against the actual config:

### The wiring really is cheap (Hammond's objection #3 dissolves)

`flake.nix:43` already declares `overlays = [ ];`, threaded to every host at line 47 (`inherit system overlays`) and line 86 (`nixpkgs.overlays = overlays ++ extraOverlays`). So the change is: add the input, set `overlays = [ seeds.overlays.default ]`, and `modules/packages.nix` says `seeds` instead of `(callPackage ../packages/seeds.nix { })`. The `extraSpecialArgs` plumbing Hammond costed out is the expensive route we simply don't take — he noted the cheap route himself and then kept pricing the expensive one.

### The marketplace-path objection is weaker than presented (his objection #2)

The load-bearing property is "identical `/nix/store` path across boost/molt/titan" — because Claude Code normalizes marketplace `path` to absolute and won't expand `~`/`$HOME`, so a `$HOME`-relative path churns `settings.json` between Linux and macOS hosts. See `modules/claude-code.nix:619-635` and memory `reference_claude_marketplace_path_no_home_expansion`.

A flake input preserves that property: inputs are pinned by `narHash` in `flake.lock` and land at a content-addressed store path, identical on every host — same guarantee as the `fetchFromGitHub` FOD.

More decisively: **that path already changes on every seeds release today.** New tag -> new rev -> new FOD hash -> new store path -> marketplace path rewritten. Per-release churn is the status quo, not a new cost. Switching to a flake input adds exactly one additional rewrite, once. Not a reason to decline.

### The payoff Hammond mismeasured (his objection #1)

He priced the benefit as "`nix flake update seeds` instead of hand-editing 2 lines — ~2 minutes, three times so far." That measures convenience. The actual benefit is **single source of truth**.

`packages/seeds.nix:28-37` hand-maintains, in a *different repo from `pyproject.toml`*, with nothing enforcing agreement:
- the runtime dependency list (`click`, `flask`)
- the `pythonRelaxDeps = [ "flask" ]` workaround for nixpkgs shipping flask 3.1.2 against our `>=3.1.3` floor

If seeds gains a third runtime dependency, nothing signals it. The home-manager build either breaks on the next switch or silently ships a package missing a dep. That's an unenforced cross-repo coupling — a correctness problem, not a convenience one.

With the flake in the seeds repo, that list sits beside `pyproject.toml`, changes in the same commit as the dependency itself, and is exercised by seeds' own CI.

### Second payoff: dogfooding the public install path

Consuming our own published flake means the public path is continuously verified. If `nix run github:outcomesinsights/seeds` breaks for strangers, it breaks for @aguynamedryan first. A CI `nix build` job proves the flake *builds*; it does not prove the *consumption* story works. Being on the same path as everyone else does.

### Implementation detail to get right

Hammond suggested `src = ./.;` plus `pytestCheckHook` (a genuine quality gain over the current `doCheck = false`, since `src = ./.` carries `tests/` along). But if home-manager consumes the flake and ever builds from source, that makes every rebuild run the full test suite. Prefer exposing tests via a `checks.default` output rather than gating `packages.default` on them.

### Direction (not yet a decision — needs beads before building)

Lean YES on both counts, reversing Hammond's "public-facing only" recommendation:
1. Ship `flake.nix` in the seeds repo — `packages.default`, `apps.default`, `overlays.default`, `devShells.default`, `checks.default`.
2. Add a `nix build` job to `.github/workflows/ci.yml` — non-negotiable prerequisite; a silently-rotting flake is a broken README promise.
3. **Do** switch home-manager to consume it via the overlay, and retire `packages/seeds.nix`. Accept the one-time marketplace-path rewrite.

Still orthogonal to the PyPI naming question (seeds-95) — a repo-local flake uses `src = ./.;` and never touches PyPI. Don't couple them.

Retained from Hammond unchanged: `buildPythonApplication`, NOT uv2nix (two runtime deps, both first-class in nixpkgs; uv2nix would add three inputs and track uv's lock format). Hatchling is a non-issue. The `src/seeds/plugin` data files are a non-issue — verified present in the built store output, swept in by the wheel `packages` directive, no `postInstall` needed.


---

## Promoted to beads (2026-07-26)

- **seeds-0y4** (P2, feature) — Add flake.nix so seeds is installable via Nix. Carries the locked decisions: buildPythonApplication not uv2nix, version parsed from `__init__.py`, tests in `checks.default` not `doCheck`, must export `overlays.default`.
- **seeds-80g** (P2, task) — Add nix build job to CI so the flake can't silently rot. Depends on seeds-0y4.
- **hm-0jz** (P3, task) — Consume seeds' own flake; retire `packages/seeds.nix`. Filed in the **home-manager repo's** tracker (`~/.config/home-manager`), since that's where the files live. bd can't express the cross-repo dependency, so the blocker is written into the description: needs seeds-0y4 + seeds-80g closed AND the seeds repo pushed to GitHub (the flake input fetches `github:outcomesinsights/seeds`, so a local-only commit is invisible to it).

@aguynamedryan's override of Hammond's "public-facing only" recommendation is quoted verbatim in hm-0jz so the judgment survives the handoff.
