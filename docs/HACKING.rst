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

``tests/test_generate.py`` is skipped: ``generate.py`` imports pip
internals that were removed after the pip 20.x line. It is replaced
together with that module, see :ref:`adr-0001`.

To test all supported platforms, run ``nix-build ./release.nix`` - this is
actually what CI does.


Changing the dependencies
-------------------------

When changing setup.py you should also run pip2nix to regenerate
python-packages.nix. I you don't have a working copy around, run
``./bootstrap.sh`` from top level directory. The script will install pip2nix
with pip into a virtualenv, and use that to generate python-packages.nix.


Releasing
---------

::

    nix-shell ./release-shell.nix
    bumpversion dev
    rm -rf pip2nix.egg-info/ dist/
    nix-shell --pure --run 'python ./setup.py sdist'
    twine upload dist/*
    bumpversion --no-tag minor
