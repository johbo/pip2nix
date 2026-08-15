from textwrap import dedent

import pytest

from pip2nix.models.package import source_to_nix
from pip2nix.models.source import Source
from pip2nix.prefetch import prefetch_git


pytestmark = pytest.mark.nix


def test_prefetch_git_fetches_the_branch_head(remote):
    _hash, revision, _checkout = prefetch_git(remote.url, 'feature')

    assert revision == remote.sha('refs/heads/feature')


@pytest.mark.network
def test_prefetches_a_url_without_a_known_digest():
    source = Source.from_url(
        'https://pypi.python.org/packages/source/p/pip/pip-7.0.3.tar.gz')

    assert source_to_nix(source) == dedent('''\
        fetchurl {
          url = "https://pypi.python.org/packages/source/p/pip/pip-7.0.3.tar.gz";
          sha256 = "1zdgl0qsgsh71b397120y7vw3rkbisrgws2rqv5c4vbgba19iidl";
        }''')
