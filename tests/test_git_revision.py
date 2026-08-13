import os
from subprocess import check_output

import pytest

from pip2nix.models.package import (
    COMMIT_ID_RE, UnresolvableRevision, prefetch_git, resolve_git_revision)


# The developer's own settings would otherwise reach the fixture, and
# commit or tag signing makes it fail.
ISOLATED_FROM_USER_CONFIG = dict(
    os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)


def git(cwd, *args):
    return check_output(
        ['git'] + list(args),
        cwd=str(cwd),
        env=ISOLATED_FROM_USER_CONFIG).decode().strip()


class Remote(object):
    def __init__(self, path):
        self.url = 'file://{}'.format(path)
        self.path = path

    def sha(self, ref):
        return git(self.path, 'rev-parse', ref)


@pytest.fixture
def remote(tmp_path):
    """
    A repository whose every named ref differs from the default branch.

    That is what makes the tests discriminating: fetching the default
    branch head was the old behaviour, so a ref pointing at it would
    let the bug pass unnoticed.
    """
    git(tmp_path, 'init', '--initial-branch', 'main', '--quiet')
    git(tmp_path, 'config', 'user.email', 'stub-user@corp.example')
    git(tmp_path, 'config', 'user.name', 'stub-user')
    git(tmp_path, 'commit', '--allow-empty', '--quiet', '-m', 'Initial commit')
    git(tmp_path, 'branch', 'shared')
    git(tmp_path, 'tag', 'v1')
    git(tmp_path, 'commit', '--allow-empty', '--quiet', '-m', 'Second commit')
    git(tmp_path, 'branch', 'feature')
    git(tmp_path, 'tag', 'shared')
    git(tmp_path, 'commit', '--allow-empty', '--quiet', '-m', 'Third commit')

    return Remote(tmp_path)


def test_bare_branch_name(remote):
    assert resolve_git_revision(
        remote.url, 'feature') == remote.sha('refs/heads/feature')


def test_bare_tag_name(remote):
    assert resolve_git_revision(remote.url, 'v1') == remote.sha('refs/tags/v1')


def test_branch_wins_over_tag_of_the_same_name(remote):
    assert resolve_git_revision(
        remote.url, 'shared') == remote.sha('refs/heads/shared')


def test_qualified_branch_ref(remote):
    assert resolve_git_revision(
        remote.url, 'refs/heads/feature') == remote.sha('refs/heads/feature')


def test_qualified_tag_ref(remote):
    assert resolve_git_revision(
        remote.url, 'refs/tags/shared') == remote.sha('refs/tags/shared')


def test_a_commit_id_is_taken_without_contacting_the_remote():
    unreachable = 'file:///no/such/repository'

    assert resolve_git_revision(unreachable, 'a' * 40) == 'a' * 40


def test_unresolvable_ref_raises(remote):
    with pytest.raises(UnresolvableRevision):
        resolve_git_revision(remote.url, 'no-such-ref')


def test_prefetch_git_fetches_the_branch_head(remote):
    _hash, revision, _checkout = prefetch_git(remote.url, 'feature')

    assert revision == remote.sha('refs/heads/feature')


@pytest.mark.parametrize('rev, is_commit_id', [
    ('a' * 40, True),
    ('A' * 40, True),
    ('0123456789abcdef0123456789abcdef01234567', True),
    ('a' * 39, False),
    ('a' * 41, False),
    ('a' * 64, False),
    ('main', False),
    ('refs/heads/main', False),
    ('', False),
])
def test_commit_ids_are_recognized_as_pip_does(rev, is_commit_id):
    assert bool(COMMIT_ID_RE.match(rev)) == is_commit_id
