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
owns the problem; pip2nix owns the translation. See :ref:`adr-0001`.

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

Rendering
---------

``models/package.py``
    Renders one ``buildPythonPackage`` call, and the ``fetchurl``,
    ``fetchgit`` or ``fetchhg`` expression for its source.

``models/source.py``
    ``Source``: scheme, url, path and an optional hash. The descriptor
    the renderer consumes, in place of pip's ``Link``.

``output.py``
    Renders every package, then writes the file.

A generation run
================

1. ``cli.py`` loads the configuration and merges the command line over
   it.
2. ``report.py`` derives pip's argument vector from it and runs
   ``pip install --dry-run --ignore-installed --report`` into a
   temporary directory it owns.
3. The report's ``version`` field is checked before anything in it is
   read.
4. ``dependencies.py`` attributes the edges: markers are evaluated
   against the environment the report resolved for, extras are
   propagated to the packages they reach, and the result is
   intersected with the resolved set.
5. Each entry becomes a package with a source carrying the hash the
   index published.
6. ``output.py`` renders every package -- prefetching only sources
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

Being replaced
==============

``generate.py`` and ``models/requirement_set.py`` drive pip's private
resolver API and have no caller left; the metadata helpers in
``models/package.py`` still import ``pip._internal`` and
``pkg_resources``. All of it goes once the report path covers what the
old one did.
