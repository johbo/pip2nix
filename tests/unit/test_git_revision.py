import pytest

from pip2nix.prefetch import COMMIT_ID_RE, UnresolvableRevision, resolve_git_revision


def test_bare_branch_name(remote):
    assert resolve_git_revision(remote.url, "feature") == remote.sha(
        "refs/heads/feature"
    )


def test_bare_tag_name(remote):
    assert resolve_git_revision(remote.url, "v1") == remote.sha("refs/tags/v1")


def test_branch_wins_over_tag_of_the_same_name(remote):
    assert resolve_git_revision(remote.url, "shared") == remote.sha("refs/heads/shared")


def test_qualified_branch_ref(remote):
    assert resolve_git_revision(remote.url, "refs/heads/feature") == remote.sha(
        "refs/heads/feature"
    )


def test_qualified_tag_ref(remote):
    assert resolve_git_revision(remote.url, "refs/tags/shared") == remote.sha(
        "refs/tags/shared"
    )


def test_a_commit_id_is_taken_without_contacting_the_remote():
    unreachable = "file:///no/such/repository"

    assert resolve_git_revision(unreachable, "a" * 40) == "a" * 40


def test_unresolvable_ref_raises(remote):
    with pytest.raises(UnresolvableRevision):
        resolve_git_revision(remote.url, "no-such-ref")


@pytest.mark.parametrize(
    "rev, is_commit_id",
    [
        ("a" * 40, True),
        ("A" * 40, True),
        ("0123456789abcdef0123456789abcdef01234567", True),
        ("a" * 39, False),
        ("a" * 41, False),
        ("a" * 64, False),
        ("main", False),
        ("refs/heads/main", False),
        ("", False),
    ],
)
def test_commit_ids_are_recognized_as_pip_does(rev, is_commit_id):
    assert bool(COMMIT_ID_RE.match(rev)) == is_commit_id
