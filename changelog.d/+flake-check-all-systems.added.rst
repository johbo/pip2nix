Check the flake on every system it names, as ``just flake-check`` and
as a job of its own in CI. ``nix flake check`` alone covers the system
running it, so an output that fails to evaluate on one of the others
stayed invisible until somebody built it. The run exits zero with
warnings present, so its output is worth reading even when it passes.
