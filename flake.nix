{
  inputs = {
    nixpkgs = {
      type = "github";
      owner = "NixOS";
      repo = "nixpkgs";
      # TODO: Interim step, working state on darwin aarch64
      rev = "c27e7255b8907b54ff6ddb6423110e2ea0139414";
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
        packages = import ./release.nix {
          pkgs = import nixpkgs {
            inherit system;
          };
        };
      in
      {
        packages =
          (builtins.listToAttrs (
            builtins.map (subkey: {
              name = "pip2nix_${subkey}";
              value = packages.pip2nix.${subkey};
            }) (builtins.attrNames packages.pip2nix)
          ))
          // {
            docs = packages.docs;
            default = packages.pip2nix.python311;
          };
      }
    );
}
