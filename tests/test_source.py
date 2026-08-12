import pytest

from pip2nix.models.source import Source


WHEEL_URL = ('https://index.example/packages/certifi-2026.1.1-py3-none-any.whl')


def test_derives_scheme_and_path_from_a_url():
    source = Source.from_url(WHEEL_URL)
    assert source.scheme == 'https'
    assert source.path == '/packages/certifi-2026.1.1-py3-none-any.whl'


def test_drops_the_fragment_from_the_url():
    source = Source.from_url(WHEEL_URL + '#sha256=' + 'ab' * 32)
    assert source.url == WHEEL_URL


def test_keeps_the_digest_it_is_given():
    source = Source.from_url(WHEEL_URL, sha256='ab' * 32)
    assert source.sha256 == 'ab' * 32


def test_has_no_digest_by_default():
    assert Source.from_url(WHEEL_URL).sha256 is None


def test_unquotes_the_path_of_a_file_url():
    source = Source.from_url('file:///tmp/a%20project')
    assert source.scheme == 'file'
    assert source.path == '/tmp/a project'


def test_a_registry_url_is_no_repository():
    source = Source.from_url(WHEEL_URL)
    assert source.vcs is None
    assert source.rev is None


@pytest.mark.parametrize('url, vcs, repository_url, rev', [
    ('git+https://git.example/repo@main',
     'git', 'https://git.example/repo', 'main'),
    ('git+https://git.example/bv/modules/account@refs/heads/branches/7.0',
     'git', 'https://git.example/bv/modules/account', 'refs/heads/branches/7.0'),
    ('git+file:///tmp/repo@main', 'git', 'file:///tmp/repo', 'main'),
    ('git+https://git.example/repo', 'git', 'https://git.example/repo', None),
    ('hg+https://hg.example/repo', 'hg', 'https://hg.example/repo', None),
])
def test_decomposes_a_repository_url(url, vcs, repository_url, rev):
    source = Source.from_url(url)
    assert (source.vcs, source.url, source.rev) == (vcs, repository_url, rev)


@pytest.mark.parametrize('url, repository_url, rev', [
    ('git+ssh://git@git.example/org/repo', 'ssh://git@git.example/org/repo',
     None),
    ('git+ssh://git@git.example/org/repo@v1.0',
     'ssh://git@git.example/org/repo', 'v1.0'),
])
def test_userinfo_is_not_taken_for_a_revision(url, repository_url, rev):
    source = Source.from_url(url)
    assert (source.url, source.rev) == (repository_url, rev)


def test_a_repository_url_keeps_the_transport_as_its_scheme():
    assert Source.from_url('git+https://git.example/repo@main').scheme == 'https'
