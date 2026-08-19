import pytest

from pip2nix.prefetch import prefetch_git


pytestmark = pytest.mark.nix


def test_prefetch_git_fetches_the_branch_head(remote):
    _hash, revision, _checkout = prefetch_git(remote.url, "feature")

    assert revision == remote.sha("refs/heads/feature")


def test_prefetch_git_reuses_a_store_path_it_already_has(remote):
    hash, _revision, path = prefetch_git(remote.url, "feature")

    reused = prefetch_git(remote.url, remote.sha("refs/heads/feature"), hash)

    assert reused == (hash, remote.sha("refs/heads/feature"), path)
