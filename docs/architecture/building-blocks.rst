===============
Building blocks
===============

The layering is conceptual rather than physical -- at roughly 1500
lines a flat module layout carries it -- but the dependency direction
is real: nothing below the adapter knows that pip exists, and rendering
imports nothing from infrastructure.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Block
     - Modules
   * - Composition root
     - ``cli.py``
   * - Adapter
     - ``config.py``, ``report.py``, ``dependencies.py``,
       ``build_system.py``
   * - Rendering
     - ``models/package.py``, ``models/source.py``,
       ``models/rendering.py``, ``models/license.py``,
       ``nix_base32.py``, ``output.py``
   * - Infrastructure
     - ``resolver.py``, ``prefetch.py``, ``licenses.py``,
       ``resources.py``
   * - Below every block
     - ``errors.py``

Composition root
================

Resolves everything external to one run and hands it inward: the
configuration, the interpreter that runs pip, the resolver built from
both, the collaborators the renderer needs, and the path the output is
written to. Nothing below it constructs a collaborator of its own.

It is the only block that reads an environment variable, and the only
place a failed run becomes a message rather than a traceback --
resolving and rendering are reported together, because both reach the
network and the store and both fail in ways a user can act on.

Adapter
=======

Turns the two external formats into the values the rest of the run
consumes: ``pip2nix.ini``, validated against ``confspec.ini``, and
pip's installation report.

``config.py`` sits here rather than with the composition root because it
is a parser and a data type holding no wiring. The search for a
configuration file walks up from the working directory, which is the one
piece of the environment the composition root does not own.

Reading the report is all ``report.py`` does. It is handed a
``Resolver`` rather than running pip, and the run's ``Sources`` rather
than reaching for a prefetch, so nothing below this block knows pip
exists.

The adapter owns the one question the report cannot answer. Core
metadata carries no build-system field, so ``build_system.py`` reads
``pyproject.toml`` out of the source itself -- a directory, an archive
or a checkout -- and whether the table is there at all is what decides
the builder. ``dependencies.py`` rebuilds the edges the report does not
carry, evaluating markers and propagating extras over report data
alone.

Rendering
=========

Turns those values into the Nix expression and writes it.
``PythonPackage`` carries ``buildPythonPackage`` arguments rather than
facts about a Python package, so it renders itself instead of being
rendered by something else. ``Source`` describes where a package's code
comes from, in place of pip's ``Link``. ``NixLicenses`` renders the
``meta.license`` field and ``nix_base32.py`` the base32 alphabet Nix
reads a hash in.

``output.py`` renders every package before it opens the output file, so
a failed run leaves the previous one intact instead of truncating it to
an unparseable fragment. It also reads that previous file back,
recovering the hash recorded for each repository under its url and
revision. An archive needs none: the index publishes its hash, so the
report always carries one.

What this block needs and the report does not carry -- a source hash, a
license attribute -- arrives as ``Sources`` and ``NixLicenses``,
bundled into ``Rendering`` by the composition root. See
:ref:`ADR-0009 <adr-0009>` for why they are resolved while rendering
and :ref:`ADR-0010 <adr-0010>` for why they are handed in.

Infrastructure
==============

Everything that leaves the process. Every subprocess a generation run
starts belongs to this block: pip, from ``resolver.py``;
``nix-prefetch-git``, ``nix-prefetch-url`` and ``git ls-remote``, from
``prefetch.py``; ``nix-instantiate``, from ``licenses.py``, which is how
``lib.licenses`` answers what nixpkgs knows about a license.
``resources.py`` reads the packaged templates and the configuration
spec.

Each of these is constructed in the composition root and handed to
whoever needs it, which is why neither the adapter nor the renderer
carries a subprocess of its own.

Below every block
=================

``errors.py`` holds the failures a generation run reports to its user:
``ReportError``, and ``UnresolvableRevision`` as a kind of it, so the
composition root reports both by catching one. Every block raises from
it and it holds nothing else, which is what keeps none of them importing
another -- including the renderer, which refuses a source without a
revision and would otherwise have to reach the adapter to say so.

The seam the guards cannot see
==============================

Three tests enforce the boundaries above rather than describing them:
``test_adapter_independence.py``, ``test_renderer_independence.py`` and
``test_pip_independence.py``. All three check imports.

One collaborator is used at runtime rather than at import. Rendering a
``fetchgit`` source calls ``Sources.repository``, which reaches
``nix-prefetch-git``, so the rendering block starts a subprocess and a
clone in the middle of building a string. The dependency direction is
intact -- the call arrives through a collaborator the composition root
passed in, and no import crosses -- but no guard can see it, and it is
the reason ``output.py`` finishes rendering before it opens the output
file. :ref:`ADR-0009 <adr-0009>` records the decision and what it costs.
