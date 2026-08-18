"""
Stand-ins for what the composition root hands the renderer and the adapter.
"""

from types import SimpleNamespace

from pip2nix.models.license import NixLicenses
from pip2nix.models.rendering import Rendering


def rendering(**overrides):
    """
    A `Rendering` whose unsupplied collaborators refuse to be called, so
    that a renderer reaching for one it was not given says so.
    """
    collaborators = dict(
        prefetch_url=_refuses("prefetch_url"),
        prefetch_git=_refuses("prefetch_git"),
        nix_licenses=NixLicenses(_refuses("nix_license_attribute")),
        include_licenses=False,
        hashes={},
    )
    return Rendering(**collaborators | overrides)


def resolver(**overrides):
    """
    A resolver whose unsupplied passes refuse to be run, so that a
    translation reaching for one it was not given says so.
    """
    passes = dict(
        check_version=_refuses("check_version"),
        resolve=_refuses("resolve"),
        resolve_source=_refuses("resolve_source"),
    )
    return SimpleNamespace(**passes | overrides)


def nix_licenses(known):
    """
    The lookup nixpkgs would answer with, from a name to attribute map.
    """
    return NixLicenses(known.get)


def _refuses(name):
    def called(*args, **kwargs):
        raise AssertionError(f"Reached for {name}, which was not supplied.")

    return called
