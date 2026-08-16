Hacking on pip2nix
==================

Development environment
-----------------------

Running ``nix develop`` in the repository drops you into a shell with the
pip2nix dependencies, ``pytest`` and ``just`` available. The shell's own
Python carries no pip, so it points ``PIP2NIX_PYTHON_EXECUTABLE`` at one
that does -- the interpreter pip2nix drives, as the built package wraps
it.

The repeated commands are recipes in the ``justfile``, which is also what
the CI workflow runs, so the two cannot drift. ``just --list`` shows
them.

Running tests
-------------

The suite under ``tests/unit`` needs neither nix nor the network, which
is what makes it the one to run while working::

    just test

Everything needing external infrastructure lives under
``tests/integration``, which runs all of itself and fails rather than
skips when a tool is missing::

    just test-integration

Two markers say which infrastructure: ``nix`` for the tests calling
``nix-instantiate`` or a ``nix-prefetch`` tool, ``network`` for those
resolving against a real package index. A machine can have one without
the other, so either half runs alone::

    pytest tests/integration/ -m "not network"

``just test-all`` runs both suites, and a bare ``pytest`` collects only
the fast one. The tests that resolve for real do so against a pip cache
of their own, because pip caches a wheel it built and a warm cache hides
the cost they exist to catch -- see :ref:`ADR-0005 <adr-0005>`.

To build against every supported Python version, and the documentation
along with them::

    just build-all

None of those run the test suite, because the generated derivations set
``doCheck = false``. That is why CI runs each suite as a job of its
own.


Changing the dependencies
-------------------------

When changing the dependencies in ``pyproject.toml`` you should also
regenerate python-packages.nix, with the pip2nix you just built. The repository carries a
``pip2nix.ini`` naming itself as the requirement, so from the top level
directory::

    just regenerate

``--licenses`` is what fills the ``meta`` blocks the committed file
carries, and it needs a ``<nixpkgs>`` the generator can evaluate.

The result builds as generated. ``setuptools`` and ``wheel`` stay out
of the set through ``excluded_packages``, which is what the build needs
of it: the interpreter that builds pip2nix already provides them, and a
second definition fails ``pythonCatchConflictsPhase``. See
:doc:`configuration`.

Run ``just build`` again before committing: a regeneration that breaks
the build is the failure mode this step exists to catch.

When it does break, ``just regenerate`` cannot fix it -- it needs a
pip2nix built from the package set that is broken. ``just bootstrap``
is the way back: it installs pip2nix into a plain virtualenv, from
source and without Nix, and ``_bootstrap_env/bin/pip2nix generate
--licenses`` then writes a fresh file.

A checkout older than the 0.10.0 release fails ``just regenerate``
before it starts, with ``bad magic number in 'pip2nix.egg_writer'``.
Two leftovers make that message between them: a ``pip2nix.egg-info``
declaring an entry point for a module that has since been removed, and
a ``.pyc`` with no source beside it, which Python imports anyway.
``just clean`` removes both, along with every other build output::

    just clean && just regenerate


Releasing
---------

Changelog entries go under the ``Unreleased`` heading, which the version
bump turns into the heading of the release::

    nix run nixpkgs#bump-my-version -- bump minor
    git commit -a -m "Release 0.11.0"
    git tag v0.11.0
    git push && git push --tags

The bump writes the version into ``pyproject.toml``,
``pip2nix/__init__.py``, ``docs/conf.py`` and the two generated lines
in ``python-packages.nix``.
It neither commits nor tags on its own, so the two steps above are
separate.

.. warning::

   Publishing to PyPI is not part of this. ``release-shell.nix`` builds
   from ``python36Packages``, which nixpkgs no longer carries, and the
   package set it reads was generated in 2018.
