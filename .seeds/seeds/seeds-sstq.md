---
id: seeds-sstq
title: Deploying seeds means deploying main, not the release — the flake input has no ref pin, so a tag and what ships can diverge
status: captured
type: concern
created_at: 2026-08-31T19:40:37.308912+00:00
updated_at: 2026-08-31T19:40:37.308912+00:00
tags:
  - release
  - nix
  - flake
  - deployment
  - versioning
  - tags
  - 2026-08-31
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Surfaced during the v0.6.0 deploy, 2026-08-31. Not hypothetical — it happened on the first release where anyone looked.

## What happened

`~/.config/home-manager/flake.nix` declares the input with no `ref` or `tag`:

    seeds = { url = "github:outcomesinsights/seeds"; inputs.nixpkgs.follows = "nixpkgs"; };

so it tracks the **default branch**. Between pushing v0.6.0 and running `just update-seeds`, `main` moved one commit past the tag — a Dependabot merge (`e789ac8`, mypy floor `>=2.3.0` -> `>=2.3.1`, PR #30) landed in the window.

Result: the flake.lock pinned `e789ac8`, not the tag's `f390761`. **What is installed on titan is v0.6.0 plus one commit that was never part of the release.**

This instance is harmless — a dev-dependency constraint, no runtime code touched, and `__version__` at that rev is still `0.6.0`, so `seeds --version` tells the truth. The shape is not harmless: **"deploy the release" and "deploy whatever main is" are currently the same command**, and nothing announces when they differ.

## Why it matters more than it looks

- `seeds --version` reports the version string baked into `src/seeds/__init__.py`, which only changes at a bump. So any number of post-tag commits can ship while the binary still claims to be the tagged release. The version is not a reliable identifier of what is running.
- The window is not small. It is however long passes between pushing a tag and running the update — and on a multi-host fleet each host updates at a different moment, so **two hosts can both report 0.6.0 and be running different code**. boost and molt are still on 0.5.0 as of this writing and will pick up whatever main is when they switch.
- The failure mode is silent by construction. Nothing in the deploy path compares the locked rev against the tag.

## The fork

- **(A) Pin the input to the tag** — `url = "github:outcomesinsights/seeds/v0.6.0"` or a `ref`. Deploys become exactly the release; a bump becomes an explicit edit rather than `nix flake update seeds` picking up whatever landed. Costs: the bump is no longer a lock-only change, and picking up an urgent fix needs a tag rather than a merge to main.
- **(B) Keep tracking main, and make the divergence visible** — have the update recipe report when the locked rev is not the newest tag, so the operator at least knows they are shipping main-plus-N.
- **(C) Leave it** — accept that the fleet tracks main and that tags are release *markers* rather than deployment targets. Defensible for a single-maintainer tool, and it is the current de facto arrangement; it just should be a choice rather than an accident.

Hammond deliberately did NOT pin to the tag while doing the bump, on the grounds that changing the tracking arrangement is not a version bump's business. That was the right call and it is why this is a seed rather than a silent change.

## Where the fix lands

The input is declared in `~/.config/home-manager/flake.nix`, so (A) and (B) are home-manager changes rather than changes to this repo. But the question is about how seeds is *consumed* and whether its tags are meant to be deployable, which belongs to this project — hence capturing it here.

Related: the release procedure in CONTRIBUTING now documents the nix refresh path and states it depends on **main** being pushed rather than the tag. That wording is currently correct and would need revisiting under (A).
