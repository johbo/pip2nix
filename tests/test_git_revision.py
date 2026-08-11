from subprocess import check_call, check_output

import pytest

from pip2nix.models.package import UnresolvableRevision, resolve_git_revision


class Remote(object):
    def __init__(self, path):
        self.url = 'file://{}'.format(path)
        self.path = path

    def sha(self, ref):
        return check_output(
            ['git', 'rev-parse', ref], cwd=str(self.path)).decode().strip()


@pytest.fixture
def remote(tmp_path):
    """A repository with a branch and a tag of the same name."""
    def git(*args):
        check_call(['git'] + list(args), cwd=str(tmp_path))

    git('init', '--initial-branch', 'main', '--quiet')
    git('config', 'user.email', 'stub-user@corp.example')
    git('config', 'user.name', 'stub-user')
    git('config', 'commit.gpgsign', 'false')
    git('commit', '--allow-empty', '--quiet', '-m', 'Initial commit')
    git('branch', 'shared')
    git('tag', 'v1')
    git('commit', '--allow-empty', '--quiet', '-m', 'Second commit')
    git('branch', 'feature')
    git('tag', 'shared')

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


def test_commit_id_passes_through(remote):
    head = remote.sha('refs/heads/main')

    assert resolve_git_revision(remote.url, head) == head


def test_unresolvable_ref_raises(remote):
    with pytest.raises(UnresolvableRevision):
        resolve_git_revision(remote.url, 'no-such-ref')
