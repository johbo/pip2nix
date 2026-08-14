======
Design
======

Problem
=======

A Nix build needs every Python package pinned: a version, a source, a
hash, and the packages it depends on. Python's own tooling resolves
requirements well, but expresses the result in formats a Nix build
cannot consume, and re-resolves from a moving index every time it runs.

pip2nix generates that pinned description as a file meant to be
committed: readable, diffable, and reviewable like the code depending
on it.

Approach
========

Two ideas carry the design.

**Get the user eighty percent of the way, and expect the rest by
hand.** Python metadata does not describe what Nix needs for the
difficult packages, so pip2nix does not attempt them. It generates the
routine majority and assumes a hand-maintained layer on top for
everything else. See :doc:`principles`.

**Let pip resolve, and translate what it resolved.** pip runs as a
subprocess and is asked for an installation report, the documented
JSON description of what it would install. pip2nix reads that report
and renders a Nix overlay from it. Resolution stays with the tool that
owns the problem; pip2nix owns the translation. See :ref:`ADR-0001 <adr-0001>`.

Structure
=========

The layering is conceptual rather than physical -- at roughly 1500
lines a flat module layout carries it -- but the dependency direction
is real: translation and rendering import nothing from pip.

Composition root
----------------

``cli.py``
    Click commands. Resolves the configuration, decides which
    interpreter runs pip, and wires the adapter to the writer.
    Environment access lives here and nowhere else.

``config.py``
    Discovery, merging and validation of ``pip2nix.ini`` or
    ``setup.cfg`` against ``confspec.ini``. Command line options are
    merged over the file. See :doc:`../configuration`.

Adapter
-------

``report.py``
    Builds pip's argument vector, runs it, validates the report, and
    converts each entry into a package and a source. Below this
    module, nothing knows that pip exists.

``dependencies.py``
    Rebuilds the dependency edges the report does not carry, by
    evaluating environment markers and propagating extras. Pure
    functions over report data.

``build_system.py``
    Reads the ``[build-system]`` table out of a source's
    ``pyproject.toml``, whether that is a directory, an archive or a
    checkout. The report carries core metadata, which has no
    build-system field. Whether the table is there at all is what
    decides the builder, so it is reported separately from the
    requirements it names.

Rendering
---------

``models/package.py``
    Renders one ``buildPythonPackage`` call, and the ``fetchurl`` or
    ``fetchgit`` expression for its source.

``models/source.py``
    ``Source``: scheme, url, path, and either the hash of an archive or
    the version control system and revision of a repository. The
    descriptor the renderer consumes, in place of pip's ``Link``.

``output.py``
    Renders every package, then writes the file.

A generation run
================

1. ``cli.py`` loads the configuration and merges the command line over
   it.
2. ``report.py`` derives pip's argument vector from it and runs
   ``pip install --dry-run --ignore-installed --report`` into a
   temporary directory it owns. That pip has to be 22.2 or newer, the
   release that learned to write a report, which is checked before the
   run starts.
3. The report's ``version`` field is checked before anything in it is
   read.
4. The entries named by ``excluded_packages`` are dropped, before any
   edge is attributed, so that nothing left in the run can refer to
   them.
5. ``dependencies.py`` attributes the edges: markers are evaluated
   against the environment the report resolved for, extras are
   propagated to the packages they reach, and the result is
   intersected with the resolved set.
6. Each entry becomes a package: an archive carries the hash the index
   published, a repository the revision pip resolved. Under
   ``only_direct`` only the entries pip marked as requested are kept --
   after attribution, so that what is kept still propagates what it
   needs.
7. A package left holding a wheel that is built for a platform gets its
   source replaced by the project's source distribution, resolved by a
   run of its own that refuses a wheel to that package alone. A run
   with none of them starts no further resolution.
   See :ref:`ADR-0003 <adr-0003>` for which packages this reaches and
   :ref:`ADR-0005 <adr-0005>` for why each gets its own pass.
8. Every package that is built from source is read for the build
   backend it declares, which means fetching the archive or the
   checkout it will be built from. That read also decides how the
   package is built: a source declaring a ``[build-system]`` table is
   emitted as ``pyproject``, one without it as ``setuptools``, and a
   wheel as ``wheel``. The renderer is handed the answer rather than
   deriving it from the file name.
9. ``output.py`` renders every package -- prefetching only sources
   whose hash is neither in the report nor in the previously generated
   file -- and writes the result.

Rendering finishes before the output file is opened, so a failed run
leaves the previous file intact instead of truncating it.

Known limits
============

Properties of the design rather than defects awaiting a fix:

- Resolution happens against the interpreter pip runs under. A
  requirement set that resolves differently per Python version or
  platform is resolved for the generator's environment, not the
  consumer's.
- Every package is emitted with ``doCheck = false``. A green build
  proves that sources unpack and dependencies resolve, not that the
  packages work.
- Native dependencies are not discovered. They belong in the overrides
  file.
- Build backends are named, not pinned. The installation report carries
  runtime dependencies only, so a name in ``nativeBuildInputs`` is a
  reference the generated file does not define, and nixpkgs decides
  which version satisfies it. Pinning them would take a resolution pass
  of its own.
- Following from that, a build requirement pinned to an exact version
  cannot be satisfied. A ``pyproject`` build checks
  ``build-system.requires`` against the environment before it starts,
  and a range is what nixpkgs can answer -- ``httptools`` asking for
  ``setuptools==80.9.0`` is not. Such a package needs
  ``pypaBuildFlags = [ "--skip-dependency-check" ]`` in the overrides
  file. A ``setuptools`` build never reads the field, so this surfaces
  only for projects declaring a build system.
- Only git repositories are rendered. A requirement from another
  version control system fails rather than producing something
  plausible.
