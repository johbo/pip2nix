"""
What the renderer is handed to render with, since neither a source hash
nor a license attribute is in pip's report.
"""

from dataclasses import dataclass

from .license import NixLicenses
from .source import GitSources


@dataclass(frozen=True)
class Rendering:
    git_sources: GitSources
    nix_licenses: NixLicenses
    include_licenses: bool
