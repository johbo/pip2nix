import os
from textwrap import dedent

import pytest

from pip2nix.models import package
from pip2nix.models.package import source_to_nix
from pip2nix.models.source import Source

from .digests import SHA256_HEX


WHEEL_URL = 'https://index.example/packages/certifi-2026.1.1-py3-none-any.whl'


@pytest.fixture
def cwd():
    old_cwd = os.getcwd()
    yield
    os.chdir(old_cwd)


def test_file_source(cwd, tmpdir):
    os.chdir(str(tmpdir))
    assert source_to_nix(Source.from_url('file://{}'.format(tmpdir))) == './.'


def test_known_digest_renders_without_prefetching():
    source = Source.from_url(WHEEL_URL, sha256=SHA256_HEX)
    assert source_to_nix(source) == dedent('''\
        fetchurl {
          url = "https://index.example/packages/certifi-2026.1.1-py3-none-any.whl";
          sha256 = "04mmsvw5c0ps2gh6hqwkcs5gyyvmfpr32zvxmv3w68a2mn5kwm39";
        }''')


def test_cached_url_renders_without_prefetching():
    rendered = source_to_nix(Source.from_url(WHEEL_URL),
                             cache={WHEEL_URL: 'the-cached-hash'})
    assert 'sha256 = "the-cached-hash";' in rendered


def test_git_source(monkeypatch):
    prefetched = {}

    def fake_prefetch_git(url, rev):
        prefetched.update(url=url, rev=rev)
        return 'the-content-hash', 'the-resolved-commit'

    monkeypatch.setattr(package, 'prefetch_git', fake_prefetch_git)
    rendered = source_to_nix(
        Source.from_url('git+https://git.example/repo@main'))

    assert prefetched == {'url': 'https://git.example/repo', 'rev': 'main'}
    assert rendered == dedent('''\
        fetchgit {
          url = "https://git.example/repo";
          rev = "the-resolved-commit";
          sha256 = "the-content-hash";
        }''')


def test_hg_source_without_a_revision_uses_the_default_branch(monkeypatch):
    prefetched = {}

    def fake_prefetch_hg(url, rev):
        prefetched.update(url=url, rev=rev)
        return 'the-content-hash', 'the-resolved-revision'

    monkeypatch.setattr(package, 'prefetch_hg', fake_prefetch_hg)
    source_to_nix(Source.from_url('hg+https://hg.example/repo'))

    assert prefetched == {'url': 'https://hg.example/repo', 'rev': 'default'}


def test_unknown_scheme():
    with pytest.raises(NotImplementedError):
        source_to_nix(Source.from_url('ftp://index.example/certifi.tar.gz'))


@pytest.mark.xfail(
    reason="Calling nix inside the nix-build does cause trouble")
def test_prefetches_a_url_without_a_known_digest():
    source = Source.from_url(
        'https://pypi.python.org/packages/source/p/pip/pip-7.0.3.tar.gz')
    assert source_to_nix(source) == (
        'fetchurl {\n'
        '  url = "https://pypi.python.org/packages/source/p/pip/pip-7.0.3.tar.gz";\n'
        '  sha256 = "1zdgl0qsgsh71b397120y7vw3rkbisrgws2rqv5c4vbgba19iidl";\n'
        '}')
