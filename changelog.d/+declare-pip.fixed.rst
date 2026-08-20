Declare ``pip`` as a dependency, so an install outside Nix brings the
resolver it runs. Resolution drives ``python -m pip`` in the
environment pip2nix is installed into, and an environment created by
``uv`` carries no pip, which made every run of such an install fail.
