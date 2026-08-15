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

# Build pip2nix against the default Python
build:
    nix build

# Build every supported Python version and the documentation
build-all:
    nix build .#pip2nix_python311 .#pip2nix_python312 \
        .#pip2nix_python313 .#docs

# Regenerate python-packages.nix with the pip2nix just built
regenerate: build
    ./result/bin/pip2nix generate --licenses

# Build pip2nix in a virtualenv, the way back from a broken package set
bootstrap:
    python3 -m venv _bootstrap_env
    _bootstrap_env/bin/pip install -e .
