from unittest.mock import Mock

from pip2nix.models.source import Repository

from ..doubles import sources


GIT_URL = "https://git.example/repo"
COMMIT = "a" * 40


def git_source(rev=COMMIT):
    return Repository(url=GIT_URL, rev=rev)


def prefetching():
    return Mock(return_value=("the-content-hash", COMMIT, "/store/repo"))


def test_fetches_a_repository_once_however_often_it_is_asked():
    prefetch = prefetching()
    fetcher = sources(prefetch)

    fetcher.repository(git_source())
    fetcher.repository(git_source())

    prefetch.assert_called_once()


def test_hands_the_prefetch_the_hash_recorded_for_the_revision():
    prefetch = prefetching()
    fetcher = sources(prefetch, {(GIT_URL, COMMIT): "the-recorded-hash"})

    fetcher.repository(git_source())

    prefetch.assert_called_once_with(GIT_URL, COMMIT, "the-recorded-hash")


def test_hands_the_prefetch_no_hash_for_another_revision():
    prefetch = prefetching()
    fetcher = sources(prefetch, {(GIT_URL, "b" * 40): "the-recorded-hash"})

    fetcher.repository(git_source())

    prefetch.assert_called_once_with(GIT_URL, COMMIT, None)
