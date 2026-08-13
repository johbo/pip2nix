Configuration file
==================


Location
--------

pip2nix will search for a configuration file from current working directory up,
until it finds either ``pip2nix.ini`` or ``setup.cfg`` that contains
pip2nix-specific sections.


[pip2nix]
---------

requirements
    comma-separated list of packages to process.

output
    default: ``./python-packages.nix``

    Where to write the generated packages set.

only_direct
    default: ``false``

    Write only the packages that were asked for, instead of everything
    pip resolves.

    Dependencies are unaffected: a package still propagates everything it
    needs, so the generated file refers to attributes it does not define.
    nixpkgs or a lower overlay has to supply them, which is what makes
    layered package sets possible.

excluded_packages
    default: ``setuptools, wheel``

    Packages that are never written to the generated set, however they
    were resolved. Names are matched canonically, so ``zope.interface``
    and ``zope-interface`` are the same entry.

    An excluded package is neither defined nor propagated: no attribute
    is written for it, and no other package lists it under
    ``propagatedBuildInputs``. It can still be named as a build backend
    under ``nativeBuildInputs``, which the generated file does not
    define in any case -- see :doc:`architecture/design`.

    The default is what the build needs of it. The interpreter that
    builds a generated set already provides ``setuptools``, and a second
    definition fails ``pythonCatchConflictsPhase``. Shorten the list, or
    empty it, when a set genuinely needs its own version of one of them.

    Exclusion outranks a request: a package named here is dropped even
    when a requirements file asks for it directly. That is the one way
    it differs from ``only_direct``, which stops writing packages while
    leaving the edges that name them.

constraints
    comma-separated list of constraint files, passed to pip as
    ``--constraint``.

    A constraint bounds a package that something else asks for. It does
    not request the package itself, so constraining a package that
    nothing requires has no effect on the generated file.

    A constraint that contradicts a requirement fails the generation.
    Pinning ``markupsafe==3.0.2`` while a requirements file asks for
    ``markupsafe==3.0.3`` is not a narrowing, and pip reports it as
    ``ResolutionImpossible`` rather than choosing one of the two.


[pip2nix:package:…]
-------------------
