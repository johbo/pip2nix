Hacking on pip2nix
==================

Development environment
-----------------------

Running ``nix develop`` in the repository drops you into a shell with the
pip2nix dependencies, ``pytest`` with ``pytest-mock``, ``just`` and
``pre-commit`` available.
The shell's own Python carries no pip, so it points
``PIP2NIX_PYTHON_EXECUTABLE`` at one that does -- the interpreter pip2nix
drives, as the built package wraps it.

The repeated commands are recipes in the ``justfile``, which is also what
the CI workflow runs, so the two cannot drift. ``just --list`` shows
them, ``just lint`` being the one CI leaves out.

Running tests
-------------

The suite under ``tests/unit`` needs neither nix nor the network, which
is what makes it the one to run while working::

    just test

Everything needing external infrastructure lives under
``tests/integration``, which runs all of itself and fails rather than
skips when a tool is missing::

    just test-integration

Three of those tests evaluate ``<nixpkgs>`` -- the license lookup, the
profile build and the scaffolded ``default.nix`` -- and the devShell
points it at the nixpkgs the flake locks. Run the suite outside that
shell and it fails at collection instead, rather than waiting on the
flake registry, which fetches without a timeout.

Two markers say which infrastructure: ``nix`` for the tests calling
``nix-instantiate`` or a ``nix-prefetch`` tool, ``network`` for those
resolving against a real package index. A machine can have one without
the other, so either half runs alone::

    pytest tests/integration/ -m "not network"

``just test-all`` runs both suites, and a bare ``pytest`` collects only
the fast one. The tests that resolve for real do so against a pip cache
of their own, because pip caches a wheel it built and a warm cache hides
the cost they exist to catch -- see :ref:`ADR-0005 <adr-0005>`.

Use ``mocker`` or a plain test double; a guard keeps ``monkeypatch``
out of the suite.

To build against every supported Python version, and the documentation
along with them::

    just build-all

None of those run the test suite, because the generated derivations set
``doCheck = false``. That is why CI runs each suite as a job of its
own.


Formatting and linting
----------------------

``ruff`` formats and lints as a pre-commit hook, over the whole tree::

    just lint

It fetches its own environment the first time, so that run needs the
network once. ``pre-commit install`` wires it into ``git commit``
instead.

The tool is not in the development shell, because
``.pre-commit-config.yaml`` pins the version and the hook is then the
only thing that formats -- a second copy could disagree with it. Which
rules are enforced is a separate question, answered by
``[tool.ruff.lint]`` in ``pyproject.toml``: the selection is named rather
than inherited, so a release widening ruff's defaults cannot change it.
``D213`` is what holds the docstring layout, and no tool wraps prose, see
:ref:`adr-0008`.

CI leaves this recipe out: it would fetch the hook repositories on every
push, and nothing the build produces depends on the formatting.


Building the documentation
--------------------------

The environment for it comes from `sphinx-builder`_, a flake input, so
the package list behind Sphinx is not maintained here::

    just docs

``just docs-watch`` serves the result and rebuilds it as the sources
change, which is the one to work in. The input carries its own nixpkgs,
which is why the lock file holds two: the documentation environment does
not move when the generator's nixpkgs does.

The PDF is a target of its own::

    just docs-pdf

Neither ``just build-all`` nor CI builds it, because it pulls a texlive
distribution nothing else needs. So a broken PDF surfaces only when
somebody builds one.

The copyright year in ``conf.py`` and ``SOURCE_DATE_EPOCH`` in
``release.nix`` move together. Sphinx replaces a copyright year that
matches the current one with the year that variable names, so a rebuild
does not follow the wall clock, and ``stdenv`` leaves it at 1980.
Bumping one without the other renders ``2015-1980`` and warns about
nothing.

.. _sphinx-builder: https://codeberg.org/johbo/sphinx-builder


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

The tools come from a shell of their own::

    nix develop .#release

It carries ``bump-my-version``, ``twine`` and the ``pyproject-build``
frontend, so the versions follow ``flake.lock`` rather than whatever the
registry resolves to on the day of the release.

Changelog entries go under the ``Unreleased`` heading, which the version
bump turns into the heading of the release::

    bump-my-version bump minor
    git commit -a -m "Release 0.11.0"
    git tag v0.11.0
    git push && git push --tags

The bump writes the version into ``pyproject.toml``,
``pip2nix/__init__.py``, ``docs/conf.py`` and the two generated lines
in ``python-packages.nix``.
It neither commits nor tags on its own, so the two steps above are
separate.

This fork publishes nothing -- uploading to PyPI stays upstream's, for
whenever the work lands there. The steps are here so that whoever makes
that release has an environment for it::

    just dist
    twine check dist/*
    twine upload dist/*

``just dist`` builds the source distribution and the wheel without build
isolation, so the backend is the ``setuptools`` the release shell
carries rather than one fetched from PyPI mid-build. ``twine check``
reads the metadata of what came out, which is the half of an upload that
costs nothing to repeat.
