{ pkgs ? import <nixpkgs> {}
, sphinxPackages
}:

with pkgs.lib;

let

  pip2nix-src = (import ./default.nix { inherit pkgs; }).pip2nix.src;

  # Sphinx replaces a copyright year matching the current one with the
  # year of SOURCE_DATE_EPOCH, so that a rebuild does not follow the
  # wall clock. stdenv defaults it to 1980, which turns the declared
  # `2015-2026` into `2015-1980`; a real date leaves the line alone.
  # See sphinx/config.py, `_substitute_copyright_year`.
  SOURCE_DATE_EPOCH = "1767225600"; # 2026-01-01

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
      inherit SOURCE_DATE_EPOCH;
      # Not full-sphinx-env, which carries the texlive only the PDF needs.
      nativeBuildInputs = [
        sphinxPackages.sphinx-env
      ];
      buildPhase = ''
        cd docs
        sphinx-build -M html . _build
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

    docs-pdf = pkgs.stdenv.mkDerivation {
      name = "pip2nix-docs-pdf";
      src = pip2nix-src;
      inherit SOURCE_DATE_EPOCH;
      nativeBuildInputs = [
        sphinxPackages.full-sphinx-env
      ];
      buildPhase = ''
        cd docs
        # texlive generates fonts below $HOME, which the sandbox points
        # at a directory nothing may write to.
        export HOME="$TMPDIR"
        sphinx-build -M latexpdf . _build
      '';
      installPhase = ''
        mkdir $out
        cp _build/latex/*.pdf $out

        # Hydra integration
        mkdir -p $out/nix-support
        for f in $out/*.pdf; do
          echo "doc manual $f" >> "$out/nix-support/hydra-build-products"
        done
      '';
    };

  };

in jobs
