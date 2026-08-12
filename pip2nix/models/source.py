from dataclasses import dataclass
from urllib.parse import unquote, urlsplit, urlunsplit


VCS_PREFIXES = ('git+', 'hg+')


@dataclass(frozen=True)
class Source:
    """
    Where a package's code comes from, in the form the renderer needs.

    `url` is free of a fragment, so it can be emitted and used as a cache
    key as it is. `sha256` is the hex digest the index publishes, if one
    is known; converting it to what Nix wants is the renderer's business.

    A repository carries `vcs` and `rev` instead of a digest. `url` is
    then the repository alone, without the `git+` spelling pip uses and
    without the revision, which `rev` holds.
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
        for prefix in VCS_PREFIXES:
            if url.startswith(prefix):
                return cls._from_repository_url(
                    prefix[:-1], url[len(prefix):], sha256)

        parts = urlsplit(url)
        return cls(
            scheme=parts.scheme,
            url=url,
            path=unquote(parts.path),
            sha256=sha256,
        )

    @classmethod
    def _from_repository_url(cls, vcs, url, sha256):
        # The revision is split off the path rather than off the whole
        # url, so that the userinfo of an ssh url is not taken for one.
        parts = urlsplit(url)
        path, separator, rev = parts.path.rpartition('@')
        if not separator:
            path, rev = parts.path, None

        return cls(
            scheme=parts.scheme,
            url=urlunsplit(parts._replace(path=path)),
            path=unquote(path),
            sha256=sha256,
            vcs=vcs,
            rev=rev,
        )
