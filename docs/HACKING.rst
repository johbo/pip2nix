Hacking on pip2nix
==================

Development environment
-----------------------

Running ``nix develop`` in the repository drops you into a shell with the
pip2nix dependencies and ``pytest`` available.

Running tests
-------------

To run the tests::

    nix develop --command python3 -m pytest tests/

To build against every supported Python version, and the documentation
along with them::

    nix build .#pip2nix_python310 .#pip2nix_python311 \
        .#pip2nix_python312 .#pip2nix_python313 .#docs

None of those run the test suite, because the generated derivations set
``doCheck = false``.


Changing the dependencies
-------------------------

When changing setup.py you should also regenerate python-packages.nix,
with the pip2nix you just built. The repository carries a
``pip2nix.ini`` naming itself as the requirement, so from the top level
directory::

    nix build
    ./result/bin/pip2nix generate --licenses

``--licenses`` is what fills the ``meta`` blocks the committed file
carries, and it needs a ``<nixpkgs>`` the generator can evaluate.

The result builds as generated. ``setuptools`` and ``wheel`` stay out
of the set through ``excluded_packages``, which is what the build needs
of it: the interpreter that builds pip2nix already provides them, and a
second definition fails ``pythonCatchConflictsPhase``. See
:doc:`configuration`.

The committed file goes one step further and keeps ``jinja2`` and
``six`` commented out, so that nixpkgs supplies those two rather than
the generated set. That is a preference rather than a requirement, and
a regeneration undoes it.

Run ``nix build`` again before committing: a regeneration that breaks
the build is the failure mode this step exists to catch.

``bootstrap.sh`` does not do this any more. It resolves nixpkgs through
the niv sources in ``nix/``, which are pinned to releases from 2018 to
2020.


Releasing
---------

.. warning::

   The release procedure below does not run. ``release-shell.nix``
   builds from ``python36Packages``, which nixpkgs no longer carries,
   and the package set it reads was generated in 2018.

::

    nix-shell ./release-shell.nix
    bumpversion dev
    rm -rf pip2nix.egg-info/ dist/
    nix-shell --pure --run 'python ./setup.py sdist'
    twine upload dist/*
    bumpversion --no-tag minor
