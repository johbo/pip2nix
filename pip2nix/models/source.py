from dataclasses import dataclass
from urllib.parse import unquote, urlsplit


@dataclass(frozen=True)
class Source:
    """
    Where a package's code comes from, in the form the renderer needs.

    `url` is free of a fragment, so it can be emitted as it is and
    paired with `rev` into a cache key. `sha256` is the hex digest the
    index publishes, if one is known; converting it to what Nix wants is
    the renderer's business.

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
        url = url.split("#", 1)[0]
        parts = urlsplit(url)
        return cls(
            scheme=parts.scheme,
            url=url,
            path=unquote(parts.path),
            sha256=sha256,
        )


class Sources:
    def __init__(self, prefetch_repository, prefetch_archive, known_hashes):
        self._prefetch_repository = prefetch_repository
        self._prefetch_archive = prefetch_archive
        self._known_hashes = known_hashes
        self._fetched = {}

    def repository(self, source):
        key = cache_key(source)
        if key not in self._fetched:
            self._fetched[key] = GitCheckout(
                *self._prefetch_repository(
                    source.url, source.rev, self._known_hashes.get(key)
                )
            )
        return self._fetched[key]

    def local_path(self, source):
        if source.vcs == "git":
            return self.repository(source).path
        if source.scheme == "file":
            return source.path
        return self._prefetch_archive(source.url, source.sha256)


@dataclass(frozen=True)
class GitCheckout:
    sha256: str
    rev: str
    path: str


def cache_key(source):
    return (source.url, source.rev)
