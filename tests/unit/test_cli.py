from textwrap import dedent

from click.testing import CliRunner

from pip2nix.cli import generate


PACKAGE_CONFIGURATION = dedent('''\
    [pip2nix]
    requirements = .

    [pip2nix:package:pip2nix:args]
    makeWrapperArgs = '"--prefix PATH : ${pkgs.nix-prefetch-scripts}"'
''')


def test_rejects_an_editable_requirement_on_the_command_line(monkeypatch):
    monkeypatch.setattr(
        'pip2nix.report.check_pip_version', lambda python_executable: None)
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(generate, ['-e', '.'])

    assert 'Editable requirements are not supported' in result.output


def test_rejects_per_package_configuration_from_the_ini_file(monkeypatch):
    monkeypatch.setattr(
        'pip2nix.report.check_pip_version', lambda python_executable: None)
    runner = CliRunner()

    with runner.isolated_filesystem():
        with open('pip2nix.ini', 'w') as configuration:
            configuration.write(PACKAGE_CONFIGURATION)
        result = runner.invoke(generate, [])

    assert '[pip2nix:package:pip2nix]' in result.output
