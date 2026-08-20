from contextlib import chdir
from textwrap import dedent
from unittest.mock import Mock

from pip2nix.models.package import source_to_nix
from pip2nix.models.source import Archive, LocalPath, Repository

from ..doubles import rendering, sources
from .digests import SHA256_HEX
from .urls import CERTIFI, REPOSITORY


def git_source(commit_id):
    return Repository(url=REPOSITORY, commit_id=commit_id)


def test_file_source(tmpdir):
    with chdir(tmpdir):
        source = LocalPath(url=f"file://{tmpdir}", path=str(tmpdir))
        assert source_to_nix(source, rendering()) == "./."


def test_known_digest_renders_without_prefetching():
    source = Archive(
        url=CERTIFI.wheel, path="/packages/certifi.whl", sha256_hex=SHA256_HEX
    )
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

    prefetch_git.assert_called_once_with(REPOSITORY, "main", None)
    assert rendered == dedent("""\
        fetchgit {
          url = "https://git.example/repo";
          rev = "the-resolved-commit";
          sha256 = "the-content-hash";
        }""")


def test_git_source_renders_the_commit_id_it_carries():
    prefetch_git = Mock(
        side_effect=lambda url, revision, _hash: (
            "the-content-hash",
            revision,
            "/store/repo",
        )
    )

    rendered = source_to_nix(
        git_source("a" * 40), rendering(sources=sources(prefetch_git))
    )

    assert 'rev = "{}";'.format("a" * 40) in rendered
