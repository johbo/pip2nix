default:
    @just --list

# Run the fast test suite, which needs neither nix nor the network
test:
    nix develop --command python3 -m pytest tests/unit/

# Run the tests that need nix or a real package index, selectable by
# the `nix` and `network` markers
test-integration:
    nix develop --command python3 -m pytest tests/integration/

# Run every test there is
test-all: test test-integration

# Run the formatters and the linter over the whole tree. The hooks
# fetch their own environments the first time, so this one needs the
# network once
lint:
    nix develop --command pre-commit run --all-files

# Build pip2nix against the default Python
build:
    nix build

# Build every supported Python version and the documentation
build-all:
    nix build .#pip2nix_python311 .#pip2nix_python312 \
        .#pip2nix_python313 .#docs

# Build the documentation as HTML
docs:
    nix build .#docs

# Serve the documentation, rebuilding it as the sources change
docs-watch:
    nix develop .#docs --command sphinx-autobuild docs docs/_build/html

# Regenerate python-packages.nix with the pip2nix just built
regenerate: build
    ./result/bin/pip2nix generate --licenses

# Build pip2nix in a virtualenv, the way back from a broken package set
bootstrap:
    python3 -m venv _bootstrap_env
    _bootstrap_env/bin/pip install -e .

# Remove the build artifacts, including bytecode left behind by a module
# that no longer exists
clean:
    rm -rf pip2nix.egg-info dist result result-* _bootstrap_env \
        .pytest_cache docs/_build
    find pip2nix tests -name '__pycache__' -type d -prune -exec rm -rf {} +
    find pip2nix tests -name '*.pyc' -delete
    find pip2nix tests -type d -empty -delete
