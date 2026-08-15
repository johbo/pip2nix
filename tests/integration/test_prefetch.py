import pytest

from pip2nix.prefetch import prefetch_git


pytestmark = pytest.mark.nix


def test_prefetch_git_fetches_the_branch_head(remote):
    _hash, revision, _checkout = prefetch_git(remote.url, 'feature')

    assert revision == remote.sha('refs/heads/feature')
