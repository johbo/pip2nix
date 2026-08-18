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
is real: translation and rendering import nothing from pip, and
rendering imports nothing from infrastructure either.

Rendering does need a source hash and a license attribute, neither of
which the report carries. It resolves both while it renders
(:ref:`ADR-0009 <adr-0009>`), through collaborators the composition
root hands it (:ref:`ADR-0010 <adr-0010>`).

Composition root
----------------

``cli.py``
    Click commands. Resolves the configuration, decides which
    interpreter runs pip, and wires the adapter to the writer.
    Environment access lives here and nowhere else, and so does the one
    place a failed run is turned into a message rather than a traceback:
    resolving and rendering are reported together.

``config.py``
    Discovery, merging and validation of ``pip2nix.ini`` against
    ``confspec.ini``. An option given on the command line is merged
    over the file; one that is not given leaves the file alone. See
    :doc:`../configuration`.

Adapter
-------

``report.py``
    Validates the report and converts each entry into a package and a
    source. It is handed a resolver rather than running pip itself, so
    below this module nothing knows that pip exists, and it is handed
    the run's git sources rather than reaching for the prefetch.

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

``errors.py``
    The failures a generation run reports to its user: ``ReportError``,
    and ``UnresolvableRevision`` as a kind of it, so ``cli.py`` reports
    both by catching ``ReportError`` alone. It sits below every module
    that raises from it and holds nothing else, which is what keeps none
    of them importing another.

Rendering
---------

``models/package.py``
    Renders one ``buildPythonPackage`` call, and the ``fetchurl`` or
    ``fetchgit`` expression for its source. ``PythonPackage`` carries
    ``buildPythonPackage`` arguments rather than facts about a Python
    package, so it renders itself instead of being rendered by
    something else.

``models/source.py``
    ``Source``: the descriptor the renderer consumes for a package's
    origin, in place of pip's ``Link``. ``GitSources`` beside it fetches
    a repository once for the whole run, because the adapter wants the
    checkout and the renderer wants the hash of the same source.

``models/rendering.py``
    ``Rendering``: what one run renders with, beyond what the report
    carries. Constructed in ``cli.py``, which is why nothing here
    reaches for infrastructure itself.

``output.py``
    Renders every package, then writes the file. It also reads the
    previous one back, recovering the hash recorded for each source
    under its url and revision.

Infrastructure
--------------

``resolver.py``
    ``Resolver``: how pip is invoked for one run. Runs the passes, and
    refuses a pip too old to write a report. Constructed in ``cli.py``,
    which is why the adapter reaches for neither a configuration nor a
    subprocess.

``prefetch.py``
    Puts a source into the Nix store through ``nix-prefetch-git`` and
    ``nix-prefetch-url``, and resolves a git revision the way pip does.
    Every subprocess a generation run starts belongs to this layer, so
    neither the renderer nor the adapter carries one of its own.

``licenses.py``
    Maps a declared license name onto a ``nixpkgs.lib.licenses``
    attribute, through a hand-written table first and then through
    ``lib.licenses`` itself, which it queries with ``nix-instantiate``.

A generation run
================

1. ``cli.py`` loads the configuration, merges the command line over it,
   and builds the ``Resolver`` that carries it to pip.
2. ``resolver.py`` derives pip's argument vector from it and runs
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
   checkout it will be built from. Both fetches are handed the hash
   that is already known, so nix answers from the store rather than
   downloading or cloning again. That read also decides how the package
   is built: a source declaring a ``[build-system]`` table is emitted as
   ``pyproject``, one without it as ``setuptools``, and a wheel as
   ``wheel``. The renderer is handed the answer rather than deriving it
   from the file name.
9. ``output.py`` renders every package -- fetching only sources whose
   hash is neither in the report nor in the previously generated file --
   and writes the result. A repository is recorded under its url and its
   revision, both of which name immutable content, so a hash recovered
   for the pair needs no checking.

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
- Test dependencies are not generated. A consumer that turns the check
  phase on adds ``nativeCheckInputs`` in the overrides file; see
  :ref:`ADR-0011 <adr-0011>`.
- Native dependencies are not discovered. They belong in the overrides
  file.
- What a regeneration reuses is what the Nix store still holds. The
  recovered hashes let nix answer from it, but nothing roots those
  paths, so a garbage collection puts the downloads and the clones back.
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
