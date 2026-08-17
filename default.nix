{ pkgs ? import <nixpkgs> {}
, pythonPackages ? "python3Packages"
}:

with pkgs.lib;
let
  basePythonPackages = with builtins; if isAttrs pythonPackages
    then pythonPackages
    else getAttr pythonPackages pkgs;

  elem = builtins.elem;
  basename = path: last (splitString "/" path);
  startsWith = prefix: full: let
    actualPrefix = builtins.substring 0 (builtins.stringLength prefix) full;
  in actualPrefix == prefix;

  src-filter = path: type:
    let
      ext = last (splitString "." path);
      parts = last (splitString "/" path);
    in
      !elem (basename path) [
        ".git" "__pycache__" ".eggs" "_bootstrap_env" "_build"
      ] &&
      !elem ext ["egg-info" "pyc"] &&
      !startsWith "result" (basename path);

  pip2nix-src = builtins.filterSource src-filter ./.;

  pythonPackagesLocalOverrides = self: super: {
    pip2nix = super.pip2nix.overridePythonAttrs (attrs: rec {
      src = pip2nix-src;
      buildInputs = [
        pkgs.nix
      ] ++ attrs.buildInputs;
      generatorPython = self.python.withPackages(ps: with ps; [
        pip
        setuptools
      ]);
      preBuild = ''
        export NIX_PATH=nixpkgs=${pkgs.path}
        export SSL_CERT_FILE=${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt
      '';
      # Handed to the `wrapPythonPrograms` hook rather than applied by a
      # `wrapProgram` of our own. That hook runs either way, so a wrap
      # here is a second one -- and because it bakes the name it finds
      # into `sys.argv[0]`, the command would report itself as
      # `.pip2nix-wrapped`.
      makeWrapperArgs = [
        "--set" "PIP2NIX_PYTHON_EXECUTABLE" "${generatorPython}/bin/python"
        "--prefix" "PATH" ":" "${makeBinPath [
          pkgs.nix
          pkgs.nix-prefetch-git
        ]}"
      ];
      # The hook skips symlinks, so the versioned name needs no ordering
      # of its own.
      postInstall = ''
        ln -s pip2nix $out/bin/pip2nix${self.python.pythonVersion}
      '';
    });

    pip2nix-for-shell = self.pip2nix.overridePythonAttrs (attrs: {
      format = "other";
      buildInputs = attrs.buildInputs ++ [
        self.pytest
        self.pytest-mock
      ];
    });

  };

  pythonPackagesGenerated = import ./python-packages.nix {
    inherit pkgs;
    inherit (pkgs) fetchurl fetchgit fetchhg;
  };

  # See
  # https://github.com/rihardsk/mautrix-hangouts-nix/commit/f5ed572b4b56b2daff002a860b5f4e00e175ed32
  myPythonPackages = let
    composedOverrides =
      (composeExtensions pythonPackagesGenerated pythonPackagesLocalOverrides);
    myPython = basePythonPackages.python.override { packageOverrides = composedOverrides; };
  in myPython.pkgs;

in myPythonPackages
