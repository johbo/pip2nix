{ pkgs ? import <nixpkgs> {}
, sphinxPackages
}:

with pkgs.lib;

let

  pip2nix-src = (import ./default.nix { inherit pkgs; }).pip2nix.src;

  make-pip2nix = {pythonVersion}: {
    name = "python${pythonVersion}";
    value = (import ./default.nix {
      inherit pkgs;
      pythonPackages = "python${pythonVersion}Packages";
    }).pip2nix;
  };

  jobs = rec {

    pip2nix = filterAttrs (n: v: n != "recurseForDerivations") (
      pkgs.lib.recurseIntoAttrs (
        builtins.listToAttrs (map make-pip2nix ([]
        ++ optional (hasAttr "python311Packages" pkgs) {pythonVersion = "311";}
        ++ optional (hasAttr "python312Packages" pkgs) {pythonVersion = "312";}
        ++ optional (hasAttr "python313Packages" pkgs) {pythonVersion = "313";}
        ))
      )
    );

    docs = pkgs.stdenv.mkDerivation {
      name = "pip2nix-docs";
      src = pip2nix-src;
      # Not full-sphinx-env, which carries the texlive only the PDF needs.
      nativeBuildInputs = [
        sphinxPackages.sphinx-env
        pkgs.gnumake
      ];
      buildPhase = ''
        cd docs
        make html
      '';
      installPhase = ''
        mkdir $out
        cp -r _build/html $out

        # Hydra integration
        mkdir -p $out/nix-support
        echo "doc manual $out/html index.html" >> \
          "$out/nix-support/hydra-build-products"
      '';
    };

  };

in jobs
