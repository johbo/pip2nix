from contextlib import chdir
from textwrap import dedent
from unittest.mock import Mock

from pip2nix.models.package import source_to_nix
from pip2nix.models.source import Archive, LocalPath, Repository

from ..doubles import rendering, sources
from .digests import SHA256_HEX


WHEEL_URL = "https://index.example/packages/certifi-2026.1.1-py3-none-any.whl"


def git_source(rev):
    return Repository(url="https://git.example/repo", rev=rev)


def test_file_source(tmpdir):
    with chdir(tmpdir):
        source = LocalPath(url=f"file://{tmpdir}", path=str(tmpdir))
        assert source_to_nix(source, rendering()) == "./."


def test_known_digest_renders_without_prefetching():
    source = Archive(url=WHEEL_URL, path="/packages/certifi.whl", sha256=SHA256_HEX)
    assert source_to_nix(source, rendering()) == dedent("""\
        fetchurl {
          url = "https://index.example/packages/certifi-2026.1.1-py3-none-any.whl";
          sha256 = "04mmsvw5c0ps2gh6hqwkcs5gyyvmfpr32zvxmv3w68a2mn5kwm39";
        }""")


def test_git_source():
    prefetch_git = Mock(
        return_value=("the-content-hash", "the-resolved-commit", "/store/repo")
    )

    rendered = source_to_nix(
        git_source("main"), rendering(sources=sources(prefetch_git))
    )

    prefetch_git.assert_called_once_with("https://git.example/repo", "main", None)
    assert rendered == dedent("""\
        fetchgit {
          url = "https://git.example/repo";
          rev = "the-resolved-commit";
          sha256 = "the-content-hash";
        }""")


def test_git_source_renders_the_revision_it_carries():
    prefetch_git = Mock(
        side_effect=lambda url, rev, _hash: ("the-content-hash", rev, "/store/repo")
    )

    rendered = source_to_nix(
        git_source("a" * 40), rendering(sources=sources(prefetch_git))
    )

    assert 'rev = "{}";'.format("a" * 40) in rendered
