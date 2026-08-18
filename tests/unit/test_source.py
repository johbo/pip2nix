from unittest.mock import Mock

from pip2nix.models.source import Source

from ..doubles import git_sources


WHEEL_URL = "https://index.example/packages/certifi-2026.1.1-py3-none-any.whl"
GIT_URL = "https://git.example/repo"
COMMIT = "a" * 40


def git_source(rev=COMMIT):
    return Source(scheme="https", url=GIT_URL, path="/repo", vcs="git", rev=rev)


def prefetching():
    return Mock(return_value=("the-content-hash", COMMIT, "/store/repo"))


def test_derives_scheme_and_path_from_a_url():
    source = Source.from_url(WHEEL_URL)
    assert source.scheme == "https"
    assert source.path == "/packages/certifi-2026.1.1-py3-none-any.whl"


def test_drops_the_fragment_from_the_url():
    source = Source.from_url(WHEEL_URL + "#sha256=" + "ab" * 32)
    assert source.url == WHEEL_URL


def test_keeps_the_digest_it_is_given():
    source = Source.from_url(WHEEL_URL, sha256="ab" * 32)
    assert source.sha256 == "ab" * 32


def test_has_no_digest_by_default():
    assert Source.from_url(WHEEL_URL).sha256 is None


def test_unquotes_the_path_of_a_file_url():
    source = Source.from_url("file:///tmp/a%20project")
    assert source.scheme == "file"
    assert source.path == "/tmp/a project"


def test_a_registry_url_is_no_repository():
    source = Source.from_url(WHEEL_URL)
    assert source.vcs is None
    assert source.rev is None


def test_fetches_a_repository_once_however_often_it_is_asked():
    prefetch = prefetching()
    sources = git_sources(prefetch)

    sources.fetch(git_source())
    sources.fetch(git_source())

    prefetch.assert_called_once()


def test_hands_the_prefetch_the_hash_recorded_for_the_revision():
    prefetch = prefetching()
    sources = git_sources(prefetch, {(GIT_URL, COMMIT): "the-recorded-hash"})

    sources.fetch(git_source())

    prefetch.assert_called_once_with(GIT_URL, COMMIT, "the-recorded-hash")


def test_hands_the_prefetch_no_hash_for_another_revision():
    prefetch = prefetching()
    sources = git_sources(prefetch, {(GIT_URL, "b" * 40): "the-recorded-hash"})

    sources.fetch(git_source())

    prefetch.assert_called_once_with(GIT_URL, COMMIT, None)
