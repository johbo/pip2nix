"""
Where a package's code comes from, in the two vocabularies it is named in.

`Source` and its kinds are what pip's report describes. `FetchGit` and
`FetchUrl` are what the generated file fetches with, and carry the
arguments of the Nix function each is named for. `Sources.resolved`
translates between them, which is where a repository's hash is fetched
and an archive's digest is re-encoded.

Which kind a source is decides what has to happen before it can be
rendered, so it is a type rather than a combination of fields that
happen to be set. The adapter reads pip's report and constructs one; no
site below infers a kind from a scheme or a digest.
"""

from dataclasses import dataclass

from .. import nix_base32
from ..errors import UnresolvableRevision


@dataclass(frozen=True)
class Source:
    """
    What every kind carries: a `url`, free of a fragment so that it can
    be emitted as it is.
    """

    url: str


@dataclass(frozen=True)
class Repository(Source):
    """
    A repository, whose hash is unknown until it has been fetched.

    `url` is the repository alone, without the `git+` spelling pip uses
    and without the commit, which `commit_id` holds.
    """

    commit_id: str

    def __post_init__(self):
        if not self.commit_id:
            raise UnresolvableRevision(
                f"No commit id given for {self.url}. Refusing to generate a "
                "source which follows whatever the default branch points at."
            )

    @property
    def cache_key(self):
        return (self.url, self.commit_id)


@dataclass(frozen=True)
class FileSource(Source):
    """
    A source that is a file rather than a repository.

    `path` is the path component of the url for an archive, and a path
    on disk for a local source.
    """

    path: str


@dataclass(frozen=True)
class Archive(FileSource):
    """
    A file the index published a digest for, in the hex the index
    publishes it in.
    """

    sha256_hex: str


@dataclass(frozen=True)
class LocalPath(FileSource):
    """
    A file or directory the run can read, with no digest to pin it.
    """


@dataclass(frozen=True)
class FetchGit:
    """
    What `fetchgit` is called with, under the names it calls them.
    """

    url: str
    rev: str
    sha256: str


@dataclass(frozen=True)
class FetchUrl:
    """
    What `fetchurl` is called with, under the names it calls them.
    `sha256` is in the base32 alphabet the attribute expects.
    """

    url: str
    sha256: str


class Sources:
    def __init__(self, prefetch_repository, prefetch_archive, known_hashes):
        self._prefetch_repository = prefetch_repository
        self._prefetch_archive = prefetch_archive
        self._known_hashes = known_hashes
        self._fetched = {}

    def repository(self, source):
        key = source.cache_key
        if key not in self._fetched:
            self._fetched[key] = GitCheckout(
                *self._prefetch_repository(
                    source.url, source.commit_id, self._known_hashes.get(key)
                )
            )
        return self._fetched[key]

    def resolved(self, source):
        """
        The source as the generated file fetches it, with nothing left
        to look up.
        """
        match source:
            case Repository():
                checkout = self.repository(source)
                return FetchGit(
                    url=source.url, rev=checkout.commit_id, sha256=checkout.sha256
                )
            case Archive():
                return FetchUrl(
                    url=source.url, sha256=nix_base32.from_hex(source.sha256_hex)
                )
            case LocalPath():
                return source

    def local_path(self, source):
        match source:
            case Repository():
                return self.repository(source).path
            case LocalPath():
                return source.path
            case Archive():
                return self._prefetch_archive(source.url, source.sha256_hex)


@dataclass(frozen=True)
class GitCheckout:
    sha256: str
    commit_id: str
    path: str
