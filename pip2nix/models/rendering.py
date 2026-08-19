"""
What the renderer is handed to render with, since neither a source hash
nor a license attribute is in pip's report.
"""

from dataclasses import dataclass

from .license import NixLicenses
from .source import Sources


@dataclass(frozen=True)
class Rendering:
    sources: Sources
    nix_licenses: NixLicenses
    include_licenses: bool
