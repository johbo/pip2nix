"""
Stand-ins for what the composition root hands the renderer.
"""

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


def nix_licenses(known):
    """
    The lookup nixpkgs would answer with, from a name to attribute map.
    """
    return NixLicenses(known.get)


def _refuses(name):
    def called(*args, **kwargs):
        raise AssertionError(f"The renderer reached for {name}.")

    return called
