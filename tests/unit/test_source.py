from unittest.mock import Mock

import pytest

from pip2nix.errors import UnresolvableRevision
from pip2nix.models.source import Archive, LocalPath, Repository, Source

from ..doubles import sources
from .digests import SHA256_HEX
from .urls import CERTIFI, REPOSITORY


COMMIT = "a" * 40


def git_source(commit_id=COMMIT):
    return Repository(url=REPOSITORY, commit_id=commit_id)


def prefetching():
    return Mock(return_value=("the-content-hash", COMMIT, "/store/repo"))


def test_a_repository_without_a_commit_id_raises():
    with pytest.raises(UnresolvableRevision):
        Repository(url=REPOSITORY, commit_id=None)


def test_fetches_a_repository_once_however_often_it_is_asked():
    prefetch = prefetching()
    fetcher = sources(prefetch)

    fetcher.repository(git_source())
    fetcher.repository(git_source())

    prefetch.assert_called_once()


def test_hands_the_prefetch_the_hash_recorded_for_the_commit_id():
    prefetch = prefetching()
    fetcher = sources(prefetch, {(REPOSITORY, COMMIT): "the-recorded-hash"})

    fetcher.repository(git_source())

    prefetch.assert_called_once_with(REPOSITORY, COMMIT, "the-recorded-hash")


def test_hands_the_prefetch_no_hash_for_another_commit_id():
    prefetch = prefetching()
    fetcher = sources(prefetch, {(REPOSITORY, "b" * 40): "the-recorded-hash"})

    fetcher.repository(git_source())

    prefetch.assert_called_once_with(REPOSITORY, COMMIT, None)


def test_the_local_path_of_a_repository_is_its_checkout():
    fetcher = sources(prefetching())

    assert fetcher.local_path(git_source()) == "/store/repo"


def test_the_local_path_of_a_local_source_is_its_own():
    fetcher = sources()

    assert fetcher.local_path(LocalPath(url="file:///src", path="/src")) == "/src"


def test_the_local_path_of_an_archive_is_where_the_prefetch_put_it():
    prefetch = Mock(return_value="/store/certifi.tar.gz")
    fetcher = sources(prefetch_archive=prefetch)

    path = fetcher.local_path(
        Archive(
            url=CERTIFI.sdist,
            path="/packages/certifi-2026.1.1.tar.gz",
            sha256=SHA256_HEX,
        )
    )

    prefetch.assert_called_once_with(CERTIFI.sdist, SHA256_HEX)
    assert path == "/store/certifi.tar.gz"


def test_every_kind_is_one_the_dispatchers_answer_for():
    """
    `Sources.local_path` and `source_to_nix` both match on these three,
    and a match nothing catches returns None rather than failing. A
    fourth kind has to be added to them, not only to this file.
    """
    assert leaf_kinds(Source) == {Repository, Archive, LocalPath}


def leaf_kinds(cls):
    subclasses = cls.__subclasses__()
    if not subclasses:
        return {cls}
    return set().union(*(leaf_kinds(subclass) for subclass in subclasses))
