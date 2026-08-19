"""
Where a package's code comes from, as the three kinds the generator has.

Which kind a source is decides what has to happen before it can be
rendered, so it is a type rather than a combination of fields that
happen to be set. The adapter reads pip's report and constructs one; no
site below infers a kind from a scheme or a digest.
"""

from dataclasses import dataclass

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
    and without the revision, which `rev` holds.
    """

    rev: str

    def __post_init__(self):
        if not self.rev:
            raise UnresolvableRevision(
                f"No revision given for {self.url}. Refusing to generate a "
                "source which follows whatever the default branch points at."
            )

    @property
    def cache_key(self):
        return (self.url, self.rev)


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
    A file the index published a digest for. `sha256` is that digest as
    hex; converting it to what Nix wants is the renderer's business.
    """

    sha256: str


@dataclass(frozen=True)
class LocalPath(FileSource):
    """
    A file or directory the run can read, with no digest to pin it.
    """


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
                    source.url, source.rev, self._known_hashes.get(key)
                )
            )
        return self._fetched[key]

    def local_path(self, source):
        match source:
            case Repository():
                return self.repository(source).path
            case LocalPath():
                return source.path
            case Archive():
                return self._prefetch_archive(source.url, source.sha256)


@dataclass(frozen=True)
class GitCheckout:
    sha256: str
    rev: str
    path: str
