{
  inputs = {
    nixpkgs = {
      type = "github";
      owner = "NixOS";
      repo = "nixpkgs";
      ref = "nixpkgs-unstable";
    };

    flake-utils = {
      type = "github";
      owner = "numtide";
      repo = "flake-utils";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgsForSystem = import nixpkgs {
          inherit system;
        };
        releasePackages = import ./release.nix {
          pkgs = pkgsForSystem;
        };
        pythonPackages = import ./default.nix {
          pkgs = pkgsForSystem;
        };
      in
      {
        packages =
          (builtins.listToAttrs (
            builtins.map (subkey: {
              name = "pip2nix_${subkey}";
              value = releasePackages.pip2nix.${subkey};
            }) (builtins.attrNames releasePackages.pip2nix)
          ))
          // {
            docs = releasePackages.docs;
            default = releasePackages.pip2nix.python313;
          };

        devShells = {
          default = pkgsForSystem.mkShell {
            inputsFrom = [
              pythonPackages.pip2nix-for-shell
            ];
            packages = [
              pkgsForSystem.just
              pkgsForSystem.nix-prefetch-git
              pkgsForSystem.nix-prefetch-hg
              pkgsForSystem.pre-commit
            ];
            # The interpreter pip2nix drives, as default.nix wraps it for
            # the built package. The shell's own Python carries no pip.
            PIP2NIX_PYTHON_EXECUTABLE = "${
              pythonPackages.python.withPackages (ps: [ ps.pip ])
            }/bin/python";
          };
        };

      }
    );
}
