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


[pip2nix:package:…]
-------------------
