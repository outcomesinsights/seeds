{
  description = "Git-backed deliberation capture for ideas that need time to grow";

  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";

  outputs =
    { self, nixpkgs }:
    let
      # x86_64-darwin is deliberately ABSENT — do not "restore" it. nixpkgs 26.11
      # dropped the platform outright, so `nixpkgs.legacyPackages.x86_64-darwin`
      # throws at EVALUATION time; no builder or emulation can work around that.
      # Declaring a platform the flake cannot even evaluate is worse than not
      # declaring it: Intel-Mac users following the README's `nix run` would hit a
      # hard error instead of a clean "unsupported system". They can still
      # `uv tool install seeds`. Reinstating it would mean pinning a second
      # nixpkgs input on the 26.05-darwin release branch (itself EOL end-of-2026)
      # plus per-system nixpkgs selection — rejected as not worth the carrying
      # cost. See seeds-808; this reverses the list set in seeds-0y4.
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;

      # Single source of truth: src/seeds/__init__.py. pyproject.toml derives the
      # version from the same file via [tool.hatch.version], so the two can never
      # drift and a release needs no edit here.
      version = builtins.head (
        builtins.match ".*__version__ = \"([^\"]+)\".*" (builtins.readFile ./src/seeds/__init__.py)
      );

      mkSeeds =
        {
          python3Packages,
          # `git` is needed ONLY by the test suite, never at runtime -- see
          # nativeCheckInputs below. Threaded in as an argument because
          # python3Packages does not reach back to the top-level package set.
          git,
          # `ripgrep` IS a runtime dependency: `seeds search` shells out to `rg`
          # (bead seeds-4co.10). Same threading reason as git.
          ripgrep,
          makeWrapper,
          runTests ? false,
        }:
        python3Packages.buildPythonApplication {
          pname = "seeds";
          inherit version;
          src = ./.;

          # pyproject.toml: build-backend = "hatchling.build".
          pyproject = true;
          build-system = [ python3Packages.hatchling ];

          # Sole runtime dependency per pyproject.toml (click>=8.1.8). Keep this
          # list in step with [project.dependencies] — that is the whole point of
          # the flake living beside pyproject.toml.
          dependencies = with python3Packages; [
            click
          ];

          # `seeds search` is a ripgrep pass over .seeds/seeds/, so `rg` has to
          # be on PATH for the installed binary -- not merely on the user's.
          # Without this wrap, `nix run github:outcomesinsights/seeds -- search`
          # works on a machine that happens to have ripgrep and fails on one
          # that does not, which is a dependency the package declared nowhere.
          # The Python side still raises a message naming ripgrep, for the
          # `pip install` / `uv tool install` routes that cannot wrap anything.
          nativeBuildInputs = [ makeWrapper ];
          makeWrapperArgs = [
            "--prefix"
            "PATH"
            ":"
            "${nixpkgs.lib.makeBinPath [ ripgrep ]}"
          ];

          # Tests are wired through checks.default, not the package: home-manager
          # consumes packages.default and should not run pytest on every rebuild.
          doCheck = runTests;
          # `git` is a TEST-only dependency, not a runtime one: src/seeds/gitstage.py
          # shells out to git but catches OSError, so `seeds sync` degrades to
          # "no commit context" when git is absent and never crashes. The tests,
          # however, BUILD real repos with real git to exercise the mixed-stage
          # guard, so the sandbox needs the binary. Without it 19 tests fail with
          # FileNotFoundError while `nix build` and every local run stay green --
          # which is exactly how this was found (seeds-ww8, 2026-08-26).
          # `ripgrep` is here as well as in makeWrapperArgs: the check phase
          # runs pytest against the source tree, not the wrapped binary, so the
          # wrapper's PATH does not reach it. Without it the twelve
          # tests/test_store.py TestSearch cases fail in the sandbox while
          # every local run stays green -- the same shape as the git omission
          # above, found the same way.
          nativeCheckInputs = nixpkgs.lib.optionals runTests [
            python3Packages.pytestCheckHook
            git
            ripgrep
          ];

          pythonImportsCheck = [ "seeds" ];

          meta = {
            description = "Git-backed deliberation capture for ideas that need time to grow";
            homepage = "https://github.com/outcomesinsights/seeds";
            license = nixpkgs.lib.licenses.mit;
            mainProgram = "seeds";
          };
        };
    in
    {
      packages = forAllSystems (system: {
        default = mkSeeds {
          inherit (nixpkgs.legacyPackages.${system})
            python3Packages
            git
            ripgrep
            makeWrapper
            ;
        };
      });

      # Consumed by ~/.config/home-manager via `overlays = [ seeds.overlays.default ];`
      overlays.default = final: _prev: {
        seeds = mkSeeds {
          inherit (final)
            python3Packages
            git
            ripgrep
            makeWrapper
            ;
        };
      };

      apps = forAllSystems (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/seeds";
        };
      });

      # The pytest suite lives HERE, not on packages.default — see doCheck above.
      # `nix flake check` (and CI) runs it; `nix build .#default` does not.
      checks = forAllSystems (system: {
        default = mkSeeds {
          inherit (nixpkgs.legacyPackages.${system})
            python3Packages
            git
            ripgrep
            makeWrapper
            ;
          runTests = true;
        };
      });

      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
            packages = with pkgs; [
              python3
              uv
              ruff
              just
              git
              ripgrep
            ];
          };
        }
      );
    };
}
