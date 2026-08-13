from dataclasses import dataclass
from urllib.parse import unquote, urlsplit


@dataclass(frozen=True)
class Source:
    """
    Where a package's code comes from, in the form the renderer needs.

    `url` is free of a fragment, so it can be emitted and used as a cache
    key as it is. `sha256` is the hex digest the index publishes, if one
    is known; converting it to what Nix wants is the renderer's business.

    A repository carries `vcs` and `rev` instead of a digest, which the
    adapter fills from the report's `vcs_info`. `url` is then the
    repository alone, without the `git+` spelling pip uses and without
    the revision, which `rev` holds.
    """

    scheme: str
    url: str
    path: str
    sha256: str | None = None
    vcs: str | None = None
    rev: str | None = None

    @classmethod
    def from_url(cls, url, sha256=None):
        url = url.split('#', 1)[0]
        parts = urlsplit(url)
        return cls(
            scheme=parts.scheme,
            url=url,
            path=unquote(parts.path),
            sha256=sha256,
        )
