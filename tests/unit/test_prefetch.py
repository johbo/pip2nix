import json
from subprocess import CalledProcessError

import pytest

from pip2nix.errors import ReportError
from pip2nix.prefetch import prefetch_git, prefetch_url_path


COMMIT = "a" * 40

GIT_URL = "https://git.example/repo"

FAILURES = [
    FileNotFoundError("nix-prefetch-url"),
    CalledProcessError(1, "nix-prefetch-url"),
]


def reported(rev):
    payload = {"sha256": "the-content-hash", "rev": rev, "path": "/store/repo"}
    return json.dumps(payload).encode("utf-8")


@pytest.mark.parametrize("failure", FAILURES)
def test_reports_a_url_whose_path_it_cannot_prefetch(mocker, failure):
    mocker.patch("pip2nix.prefetch.check_output", side_effect=failure)

    with pytest.raises(ReportError):
        prefetch_url_path("https://index.example/certifi-2026.1.1.zip", "ff" * 32)


@pytest.mark.parametrize("failure", FAILURES)
def test_reports_a_repository_it_cannot_prefetch(mocker, failure):
    mocker.patch("pip2nix.prefetch.check_output", side_effect=failure)

    with pytest.raises(ReportError):
        prefetch_git(f"https://git.example/{type(failure).__name__}", COMMIT)


@pytest.mark.parametrize("failure", FAILURES)
def test_reports_a_repository_whose_refs_it_cannot_list(mocker, failure):
    mocker.patch("pip2nix.prefetch.check_output", side_effect=failure)

    with pytest.raises(ReportError):
        prefetch_git(f"https://git.example/refs-{type(failure).__name__}", "main")


def test_offers_a_known_hash_so_the_store_can_answer(mocker):
    check_output = mocker.patch(
        "pip2nix.prefetch.check_output", return_value=reported(rev=COMMIT)
    )

    prefetch_git(GIT_URL, COMMIT, "the-recorded-hash")

    assert check_output.call_args.args[0] == [
        "nix-prefetch-git",
        GIT_URL,
        COMMIT,
        "the-recorded-hash",
    ]


def test_offers_no_hash_when_none_was_recorded(mocker):
    check_output = mocker.patch(
        "pip2nix.prefetch.check_output", return_value=reported(rev=COMMIT)
    )

    prefetch_git(GIT_URL, COMMIT)

    assert check_output.call_args.args[0] == ["nix-prefetch-git", GIT_URL, COMMIT]


def test_keeps_the_revision_a_reused_store_path_does_not_report(mocker):
    mocker.patch("pip2nix.prefetch.check_output", return_value=reported(rev=""))

    _hash, rev, _path = prefetch_git(GIT_URL, COMMIT, "the-recorded-hash")

    assert rev == COMMIT
