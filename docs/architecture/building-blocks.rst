===============
Building blocks
===============

The layering is conceptual rather than physical -- at roughly 1500
lines a flat module layout carries it -- but the dependency direction
is real: translation and rendering import nothing from pip, and
rendering imports nothing from infrastructure either.

Rendering does need a source hash and a license attribute, neither of
which the report carries. It resolves both while it renders
(:ref:`ADR-0009 <adr-0009>`), through collaborators the composition
root hands it (:ref:`ADR-0010 <adr-0010>`).

Composition root
================

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
=======

``report.py``
    Validates the report and converts each entry into a package and a
    source. It is handed a resolver rather than running pip itself, so
    below this module nothing knows that pip exists, and it is handed
    the run's sources rather than reaching for the prefetch. Neither
    import is left, which ``tests/unit/test_adapter_independence.py``
    keeps true.

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
=========

``models/package.py``
    Renders one ``buildPythonPackage`` call, and the ``fetchurl`` or
    ``fetchgit`` expression for its source. ``PythonPackage`` carries
    ``buildPythonPackage`` arguments rather than facts about a Python
    package, so it renders itself instead of being rendered by
    something else.

``models/source.py``
    ``Source``: the descriptor the renderer consumes for a package's
    origin, in place of pip's ``Link``. ``Sources`` beside it fetches
    each one once for the whole run, because the adapter wants the
    checkout and the renderer wants the hash of the same source.

``models/rendering.py``
    ``Rendering``: what one run renders with, beyond what the report
    carries. Constructed in ``cli.py``, which is why nothing here
    reaches for infrastructure itself.

``output.py``
    Renders every package, then writes the file. It also reads the
    previous one back, recovering the hash recorded for each repository
    under its url and revision. An archive needs none: the index
    publishes its hash, so the report always carries one.

Infrastructure
==============

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
