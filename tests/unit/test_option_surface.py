"""
The claims the configuration surface makes about itself.

Every option this repository has found accepted-and-ignored was found
by accident. These guard the shapes it came in: a key declared and read
by nothing, and a command-line default that quietly overwrites what a
configuration file said.
"""
import pytest
from click.testing import CliRunner

from pip2nix.cli import generate
from pip2nix.config import MERGED_CLI_OPTIONS, Config


FILE_VALUES = {
    'output': './generated.nix',
    'index_url': 'https://mirror.example/simple',
    'extra_index_url': ['https://internal.example/simple',
                        'https://vendor.example/simple'],
    'no_index': True,
    'only_direct': True,
    'licenses': True,
}


def test_every_shared_option_can_be_set_in_a_configuration_file(monkeypatch):
    assert set(FILE_VALUES) == set(MERGED_CLI_OPTIONS)

    config = configuration_from_a_file_alone(monkeypatch)

    assert {key: config['pip2nix'][key] for key in FILE_VALUES} == FILE_VALUES


@pytest.mark.parametrize('key', [
    'requirements', 'constraints', 'excluded_packages', 'extra_index_url'])
def test_a_list_option_takes_a_single_value(key):
    config = Config()
    config.merge_options({'pip2nix': {'requirements': ['.'], key: 'one'}})

    config.validate()

    assert config['pip2nix'][key] == ['one']


def configuration_from_a_file_alone(monkeypatch):
    """
    The configuration `generate` builds when a file is the only source,
    every option being left at its command-line default.
    """
    captured = []

    def capture(config, python_executable):
        captured.append(config)
        return []

    monkeypatch.setattr('pip2nix.cli.resolve_packages', capture)
    monkeypatch.setattr('pip2nix.cli.write_output',
                        lambda path, packages, licenses: None)

    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('pip2nix.ini', 'w') as configuration:
            configuration.write(as_ini(FILE_VALUES))
        runner.invoke(generate, [], catch_exceptions=False)

    return captured[0]


def as_ini(values):
    lines = ['[pip2nix]', 'requirements = .']
    lines.extend('{} = {}'.format(key, as_ini_value(value))
                 for key, value in sorted(values.items()))
    return '\n'.join(lines) + '\n'


def as_ini_value(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, list):
        return ', '.join(value)
    return value
