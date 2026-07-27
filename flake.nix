{
  description = "Git-backed deliberation capture for ideas that need time to grow";

  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
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
          runTests ? false,
        }:
        python3Packages.buildPythonApplication {
          pname = "seeds";
          inherit version;
          src = ./.;

          # pyproject.toml: build-backend = "hatchling.build".
          pyproject = true;
          build-system = [ python3Packages.hatchling ];

          # Sole runtime dependencies per pyproject.toml (click>=8.1.8, flask>=3.1.3).
          # Keep this list in step with [project.dependencies] — that is the whole
          # point of the flake living beside pyproject.toml.
          dependencies = with python3Packages; [
            click
            flask
          ];

          # nixpkgs can lag seeds' declared flask floor (>=3.1.3); the delta is a
          # no-op for our usage. Relax ONLY flask — click stays validated.
          pythonRelaxDeps = [ "flask" ];

          # Tests are wired through checks.default, not the package: home-manager
          # consumes packages.default and should not run pytest on every rebuild.
          doCheck = runTests;
          nativeCheckInputs = nixpkgs.lib.optionals runTests [ python3Packages.pytestCheckHook ];

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
        default = mkSeeds { inherit (nixpkgs.legacyPackages.${system}) python3Packages; };
      });

      # Consumed by ~/.config/home-manager via `overlays = [ seeds.overlays.default ];`
      overlays.default = final: _prev: {
        seeds = mkSeeds { inherit (final) python3Packages; };
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
          inherit (nixpkgs.legacyPackages.${system}) python3Packages;
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
            ];
          };
        }
      );
    };
}
