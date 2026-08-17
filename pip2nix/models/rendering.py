"""
What the renderer is handed to render with, since neither a source hash
nor a license attribute is in pip's report.
"""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Rendering:
    prefetch_url: Callable[[str], str]
    prefetch_git: Callable[[str, str], tuple[str, str, str]]
    include_licenses: bool
    hashes: dict[str, str]
