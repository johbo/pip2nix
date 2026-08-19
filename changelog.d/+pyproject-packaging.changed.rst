Migrate pip2nix's own packaging to ``pyproject.toml``. It decides how
to build a package from that package's ``[build-system]`` table, and
shipped a ``setup.py`` itself -- so it now declares what it expects
everything it generates to declare, and writes ``format =
"pyproject"`` for its own entry.
