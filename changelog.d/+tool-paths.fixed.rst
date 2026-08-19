Put the tools pip2nix runs on the PATH of the entry points
``default.nix`` wraps. A built pip2nix found ``nix-prefetch-url`` and
``nix-instantiate`` only where ``nix`` happened to be on the ambient
PATH, and ``nix-prefetch-git`` -- which every ``fetchgit`` source
needs -- nowhere at all.
