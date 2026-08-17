from subprocess import CalledProcessError

import pytest

from pip2nix.errors import ReportError
from pip2nix.prefetch import prefetch_git, prefetch_url, prefetch_url_path


COMMIT = "a" * 40

FAILURES = [
    FileNotFoundError("nix-prefetch-url"),
    CalledProcessError(1, "nix-prefetch-url"),
]


@pytest.mark.parametrize("failure", FAILURES)
def test_reports_a_url_it_cannot_prefetch(mocker, failure):
    mocker.patch("pip2nix.prefetch.check_output", side_effect=failure)

    with pytest.raises(ReportError):
        prefetch_url("https://index.example/certifi-2026.1.1.tar.gz")


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
