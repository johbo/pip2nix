from contextlib import chdir
from textwrap import dedent

import pytest

from pip2nix.models.package import source_to_nix
from pip2nix.models.source import Source
from pip2nix.prefetch import UnresolvableRevision

from .digests import SHA256_HEX

WHEEL_URL = "https://index.example/packages/certifi-2026.1.1-py3-none-any.whl"


def git_source(rev):
    return Source(
        scheme="https", url="https://git.example/repo", path="/repo", vcs="git", rev=rev
    )


def test_file_source(tmpdir):
    with chdir(tmpdir):
        assert source_to_nix(Source.from_url(f"file://{tmpdir}")) == "./."


def test_known_digest_renders_without_prefetching():
    source = Source.from_url(WHEEL_URL, sha256=SHA256_HEX)
    assert source_to_nix(source) == dedent("""\
        fetchurl {
          url = "https://index.example/packages/certifi-2026.1.1-py3-none-any.whl";
          sha256 = "04mmsvw5c0ps2gh6hqwkcs5gyyvmfpr32zvxmv3w68a2mn5kwm39";
        }""")


def test_cached_url_renders_without_prefetching():
    rendered = source_to_nix(
        Source.from_url(WHEEL_URL), cache={WHEEL_URL: "the-cached-hash"}
    )
    assert 'sha256 = "the-cached-hash";' in rendered


def test_git_source(mocker):
    prefetch_git = mocker.patch(
        "pip2nix.models.package.prefetch_git",
        return_value=("the-content-hash", "the-resolved-commit", "/store/repo"),
    )

    rendered = source_to_nix(git_source("main"))

    prefetch_git.assert_called_once_with("https://git.example/repo", "main")
    assert rendered == dedent("""\
        fetchgit {
          url = "https://git.example/repo";
          rev = "the-resolved-commit";
          sha256 = "the-content-hash";
        }""")


def test_git_source_renders_the_revision_it_carries(mocker):
    mocker.patch(
        "pip2nix.models.package.prefetch_git",
        side_effect=lambda url, rev: ("the-content-hash", rev, "/store/repo"),
    )

    assert 'rev = "{}";'.format("a" * 40) in source_to_nix(git_source("a" * 40))


def test_git_source_without_a_revision_raises():
    with pytest.raises(UnresolvableRevision):
        source_to_nix(git_source(None))


def test_a_repository_pip2nix_cannot_render_raises():
    source = Source(
        scheme="https", url="https://hg.example/repo", path="/repo", vcs="hg", rev="tip"
    )

    with pytest.raises(NotImplementedError):
        source_to_nix(source)


def test_unknown_scheme():
    with pytest.raises(NotImplementedError):
        source_to_nix(Source.from_url("ftp://index.example/certifi.tar.gz"))
