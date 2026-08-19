Update the nixpkgs pin from 2025-11-18 to 2026-08-17, and name the
systems the flake supports rather than taking them from
``eachDefaultSystem``. That list comes from ``nix-systems/default``,
unchanged since 2023, and still carries ``x86_64-darwin`` -- a system
nixpkgs dropped in 26.11, which made every output under it fail to
evaluate. ``python-packages.nix`` regenerates byte for byte across
the bump, pip 25.0.1 to 26.1.2 included.
