default:
    @just --list

# Run the test suite in the development shell
test:
    nix develop --command python3 -m pytest tests/

# Build pip2nix against the default Python
build:
    nix build

# Build every supported Python version and the documentation
build-all:
    nix build .#pip2nix_python310 .#pip2nix_python311 \
        .#pip2nix_python312 .#pip2nix_python313 .#docs

# Regenerate python-packages.nix with the pip2nix just built
regenerate: build
    ./result/bin/pip2nix generate --licenses

# Build pip2nix in a virtualenv, bypassing the generated package set.
# The way back when a regeneration breaks python-packages.nix.
# TODO: Drop the setuptools pin once cli.py reads its data files
# through importlib.resources instead of pkg_resources.
bootstrap:
    python3 -m venv _bootstrap_env
    _bootstrap_env/bin/pip install -e . 'setuptools<81'
