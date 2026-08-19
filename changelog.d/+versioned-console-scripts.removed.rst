Drop the versioned console scripts ``pip2nix3`` and ``pip2nix3.1``.
They were computed from ``sys.version`` slices yielding ``"3"`` and
``"3.1"`` on every supported interpreter, so all three builds
installed the same two names and neither said which interpreter it
resolves against.
