from click.testing import CliRunner

from pip2nix.cli import generate


def test_rejects_an_editable_requirement_on_the_command_line(monkeypatch):
    monkeypatch.setattr(
        'pip2nix.report.check_pip_version', lambda python_executable: None)
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(generate, ['-e', '.'])

    assert 'Editable requirements are not supported' in result.output
