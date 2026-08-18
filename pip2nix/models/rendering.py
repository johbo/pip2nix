"""
What the renderer is handed to render with, since neither a source hash
nor a license attribute is in pip's report.
"""

from collections.abc import Callable
from dataclasses import dataclass

from .license import NixLicenses
from .source import GitSources


@dataclass(frozen=True)
class Rendering:
    prefetch_url: Callable[[str], str]
    git_sources: GitSources
    nix_licenses: NixLicenses
    include_licenses: bool
    hashes: dict[tuple[str, str | None], str]
