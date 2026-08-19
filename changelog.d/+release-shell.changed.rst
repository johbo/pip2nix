Replace the release tooling with a ``nix develop .#release`` shell
carrying ``bump-my-version``, the build frontend and ``twine``, and
add ``just dist`` to build the source distribution and the wheel.
``release-shell.nix`` and the package set it read, generated in 2018
against ``python36Packages``, are gone.
