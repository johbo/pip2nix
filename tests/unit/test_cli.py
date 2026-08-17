from textwrap import dedent

from click.testing import CliRunner

from pip2nix.cli import generate
from pip2nix.errors import UnresolvableRevision


PACKAGE_CONFIGURATION = dedent("""\
    [pip2nix]
    requirements = .

    [pip2nix:package:pip2nix:args]
    makeWrapperArgs = '"--prefix PATH : ${pkgs.nix-prefetch-scripts}"'
""")

MALFORMED_REQUIREMENT = "not a requirement!"

UNRESOLVABLE_REVISION = (
    'Cannot resolve "1.16.0" to a commit in https://git.example/six.'
)

REPORT_WITH_A_GIT_SOURCE = {
    "version": "1",
    "environment": {"python_version": "3.13", "sys_platform": "linux"},
    "install": [
        {
            "requested": True,
            "metadata": {"name": "six", "version": "1.16.0"},
            "download_info": {
                "url": "https://git.example/six",
                "vcs_info": {
                    "vcs": "git",
                    "requested_revision": "1.16.0",
                    "commit_id": "65486e4383f9f411da95937451205d3c7b61b9e1",
                },
            },
        }
    ],
}

REPORT_WITH_A_MALFORMED_REQUIREMENT = {
    "version": "1",
    "environment": {"python_version": "3.13", "sys_platform": "linux"},
    "install": [
        {
            "requested": True,
            "metadata": {
                "name": "trytond",
                "version": "7.0.0",
                "requires_dist": [MALFORMED_REQUIREMENT],
            },
        }
    ],
}


def test_rejects_an_editable_requirement_on_the_command_line(mocker):
    mocker.patch("pip2nix.report.check_pip_version")
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(generate, ["-e", "."])

    assert "Editable requirements are not supported" in result.output


def test_rejects_per_package_configuration_from_the_ini_file():
    runner = CliRunner()

    with runner.isolated_filesystem():
        with open("pip2nix.ini", "w") as configuration:
            configuration.write(PACKAGE_CONFIGURATION)
        result = runner.invoke(generate, [])

    assert "[pip2nix:package:pip2nix]" in result.output


def test_reports_a_malformed_requirement_the_report_carries(mocker):
    mocker.patch("pip2nix.report.check_pip_version")
    mocker.patch(
        "pip2nix.report._read_report",
        return_value=REPORT_WITH_A_MALFORMED_REQUIREMENT,
    )
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(generate, ["trytond"])

    assert result.exit_code == 1
    assert "trytond" in result.output
    assert MALFORMED_REQUIREMENT in result.output


def test_reports_a_revision_it_cannot_resolve(mocker):
    mocker.patch("pip2nix.report.check_pip_version")
    mocker.patch("pip2nix.report._read_report", return_value=REPORT_WITH_A_GIT_SOURCE)
    mocker.patch(
        "pip2nix.report.prefetch_git",
        side_effect=UnresolvableRevision(UNRESOLVABLE_REVISION),
    )
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(generate, ["six"])

    assert result.exit_code == 1
    assert UNRESOLVABLE_REVISION in result.output
