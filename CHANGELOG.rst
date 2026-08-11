===========
 Changelog
===========


0.8.0
=====

- Resolve the revision of a git requirement the way pip does, so that a
  bare branch name works again and a branch takes precedence over a tag
  of the same name. Previously the requested revision either had to be
  written fully qualified, as `@refs/heads/main`, or the source was
  fetched from the default branch regardless of what was asked for.

- Abort the generation when a revision cannot be resolved, instead of
  dropping the package from the output.

- Keep the previously generated file intact when the generation fails,
  and exit with a non-zero status. Both used to be silent: the output
  was truncated to an unparseable fragment and the command still
  reported success.

- Drop the `toml` dependency. `pyproject.toml` is read with the standard
  library's `tomllib`.

- Adopt decision records. Significant decisions are now recorded as ADRs
  under `docs/decisions/`, rendered in the documentation as the decision
  log. The conventions are described in `docs/decisions/README.md`.

- Record the decision to generate from pip's installation report instead
  of driving pip's internal API. See ADR-0001.

- Fix job `docs` in `release.nix` to include the full sources.

- Extend tips in the documentation with trouble related to `nix-prefetch-hg`.


0.7.0
=====

- Update template for the file `default.nix` to also ignore the `.hg` folder.
  This is useful for Mercurial based projects.

  Thanks to Marcin Kuzminzki.

- Fix to quote package and dependency names and improve the readability of the
  generated output.

  Thanks to Asko Soukka.

- Adjust `release.nix` for better Hydra integration.

  Thanks to Martin Bornhold.

- Mark tests as xfail to avoid trouble when building on NixOS itself.
  Details can be found here https://github.com/johbo/pip2nix/issues/35.

- Use `python36Packages` by default inside of `default.nix`. I noticed that I
  was specifying it nearly always when working on `pip2nix`. Via `release.nix`
  we still have all Python versions easily available.

- Fix the attribute name of ZPL licenses, so that it matches the attribute names
  from Nixpkgs_.

- Add an example about `setuptools` into the generated layer with manual
  overrides. This is a useful entry when running into issues around an infinite
  recursion.

- Update docs with a hint how to run inside of `nix-shell`.

- Update docs with a pointer to examples in `pip2nix-generated`.

- Add section "Tips" to the documentation.


0.6.0
=====

- Change the file `python-packages.nix` into a function.

  To adjust import it like the following:

  .. code:: nix

      pythonPackagesGenerated = import ./python-packages.nix {
        inherit pkgs;
        inherit (pkgs) fetchurl fetchgit;
      };

- Add new attribute `pip2nix.python36` into the file `release.nix`.

- Adjust the template for the file `default.nix` to be compatible with
  the new python packages which are based on the fix point combinator.
  See https://github.com/NixOS/nixpkgs/pull/20893 for more details.


0.5.0
=====

- Fixes for git URL support, parsing the output of `nix-prefetch-git` as JSON.

- Use `nix-prefetch-url` to fetch dependencies and get their `sha256` hash.

- Allow version 9 of pip itself for better compatibility with recent nixpkgs
  versions.

- Update `python-packages.nix` and `release-python-packages.nix`. This should
  also avoid the warnings due to using `md5` as a hash type.





.. Links

.. _Nixpkgs: https://nixos.org/nixpkgs
