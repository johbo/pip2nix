"""
What the renderer is handed to render with, since a license attribute is
not in pip's report.
"""

from dataclasses import dataclass

from .license import NixLicenses


@dataclass(frozen=True)
class Rendering:
    nix_licenses: NixLicenses
    include_licenses: bool
