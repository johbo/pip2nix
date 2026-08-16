"""
Fixtures both suites need, which is what keeps them out of either one.
"""

import os
from subprocess import check_output

import pytest


# The developer's own settings would otherwise reach the fixture, and
# commit or tag signing makes it fail.
ISOLATED_FROM_USER_CONFIG = dict(
    os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull
)


@pytest.fixture
def remote(tmp_path):
    """
    A repository whose every named ref differs from the default branch.

    That is what makes the tests discriminating: fetching the default
    branch head was the old behaviour, so a ref pointing at it would
    let the bug pass unnoticed.
    """
    git(tmp_path, "init", "--initial-branch", "main", "--quiet")
    git(tmp_path, "config", "user.email", "stub-user@corp.example")
    git(tmp_path, "config", "user.name", "stub-user")
    git(tmp_path, "commit", "--allow-empty", "--quiet", "-m", "Initial commit")
    git(tmp_path, "branch", "shared")
    git(tmp_path, "tag", "v1")
    git(tmp_path, "commit", "--allow-empty", "--quiet", "-m", "Second commit")
    git(tmp_path, "branch", "feature")
    git(tmp_path, "tag", "shared")
    git(tmp_path, "commit", "--allow-empty", "--quiet", "-m", "Third commit")

    return Remote(tmp_path)


class Remote:
    def __init__(self, path):
        self.url = "file://{}".format(path)
        self.path = path

    def sha(self, ref):
        return git(self.path, "rev-parse", ref)


def git(cwd, *args):
    return (
        check_output(["git"] + list(args), cwd=str(cwd), env=ISOLATED_FROM_USER_CONFIG)
        .decode()
        .strip()
    )
