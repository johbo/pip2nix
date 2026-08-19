Hacking on pip2nix
==================

Development environment
-----------------------

``nix develop`` gives a shell with the dependencies, ``pytest``, ``just``
and ``pre-commit``. Its own Python carries no pip, so it points
``PIP2NIX_PYTHON_EXECUTABLE`` at one that does -- the interpreter pip2nix
drives, as the built package wraps it.

``just --list`` shows the recipes, and CI runs the same ones.

Running tests
-------------

The suite under ``tests/unit`` needs neither nix nor the network, which
is what makes it the one to run while working::

    just test

Everything needing external infrastructure lives under
``tests/integration``, which fails rather than skips when a tool is
missing::

    just test-integration

Run that one inside ``nix develop``. Three of its tests evaluate
``<nixpkgs>`` and the devShell points that at the nixpkgs the flake
locks; outside the shell they fail at collection rather than waiting on
the flake registry, which fetches without a timeout.

Two markers say which infrastructure a test needs -- ``nix`` for the
ones calling ``nix-instantiate`` or a ``nix-prefetch`` tool, ``network``
for those resolving against a real package index. Either half runs
alone::

    pytest tests/integration/ -m "not network"

``just test-all`` runs both suites. Use ``mocker`` or a plain test
double; a guard keeps ``monkeypatch`` out of the suite.

To build against every supported Python version, and the documentation
along with them::

    just build-all

Those derivations set ``doCheck = false``, so they run no tests. CI runs
each suite as a job of its own.

The flake is checked on every system it names, where a plain ``nix flake
check`` covers only the system running it::

    just flake-check

That is what catches a system nixpkgs has dropped, whose outputs become
an evaluation error the moment somebody builds on it. The run exits zero
with warnings present, so its output is worth reading even when it
passes.


Formatting and linting
----------------------

``ruff`` formats and lints as a pre-commit hook, over the whole tree::

    just lint

The first run fetches its own environment, so it needs the network once.
``pre-commit install`` wires it into ``git commit`` instead. CI leaves
this recipe out.

``ruff`` is not in the development shell: ``.pre-commit-config.yaml``
pins the version, and the hook is then the only thing that formats. The
rule selection is named rather than inherited, in ``[tool.ruff.lint]``
-- see :ref:`adr-0008`.


Building the documentation
--------------------------

The environment comes from `sphinx-builder`_, a flake input, so the
package list behind Sphinx is not maintained here::

    just docs

``just docs-watch`` serves the result and rebuilds it as the sources
change. The input's own ``nixpkgs`` and ``flake-utils`` follow this
flake's, so the documentation builds against the pin stated here and
the lock holds one of each.

The PDF is a target of its own, built by neither ``just build-all`` nor
CI because it pulls a texlive distribution nothing else needs, so a
broken one surfaces only when somebody builds it::

    just docs-pdf

.. _sphinx-builder: https://codeberg.org/johbo/sphinx-builder


Changing the dependencies
-------------------------

After changing the dependencies in ``pyproject.toml``, regenerate
``python-packages.nix`` with the pip2nix you just built. The repository
carries a ``pip2nix.ini`` naming itself as the requirement, so from the
top level directory::

    just regenerate

``--licenses`` fills the ``meta`` blocks the committed file carries, and
needs a ``<nixpkgs>`` the generator can evaluate. ``setuptools`` and
``wheel`` stay out of the set through ``excluded_packages``: the
interpreter that builds pip2nix already provides them, and a second
definition fails ``pythonCatchConflictsPhase``. See
:doc:`configuration`.

Run ``just build`` again before committing -- a regeneration that breaks
the build is the failure mode this step exists to catch.

When it does break, ``just regenerate`` cannot fix it, since it needs a
pip2nix built from the package set that is broken. ``just bootstrap``
installs pip2nix into a plain virtualenv, from source and without Nix,
and ``_bootstrap_env/bin/pip2nix generate --licenses`` then writes a
fresh file.

A checkout older than the 0.10.0 release fails ``just regenerate``
before it starts, with ``bad magic number in 'pip2nix.egg_writer'`` --
a stale ``pip2nix.egg-info`` declaring an entry point for a module that
has since been removed, and a ``.pyc`` with no source beside it, which
Python imports anyway. ``just clean`` removes both::

    just clean && just regenerate


Releasing
---------

The tools come from a shell of their own::

    nix develop .#release

It carries ``bump-my-version``, ``twine`` and the ``pyproject-build``
frontend, pinned through ``flake.lock`` rather than resolved on the day
of the release.

Changelog entries go under the ``Unreleased`` heading, which the version
bump turns into the heading of the release. The bump neither commits nor
tags on its own::

    bump-my-version bump minor
    git commit -a -m "Release 0.11.0"
    git tag v0.11.0
    git push && git push --tags

It writes the version into ``pyproject.toml``, ``pip2nix/__init__.py``,
``docs/conf.py`` and the two generated lines in ``python-packages.nix``.

This fork publishes nothing -- uploading to PyPI stays upstream's, for
whenever the work lands there. The steps are here so that whoever makes
that release has an environment for it::

    just dist
    twine check dist/*
    twine upload dist/*

``just dist`` builds the source distribution and the wheel without build
isolation, so the backend is the ``setuptools`` the release shell
carries rather than one fetched from PyPI mid-build.
