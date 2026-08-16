"""
The claims the configuration surface makes about itself.

Every option this repository has found accepted-and-ignored was found
by accident. These guard the shapes it came in: a key declared and read
by nothing, and a command-line default that quietly overwrites what a
configuration file said.
"""
import importlib
import inspect
import io

import configobj
import pytest
from click.testing import CliRunner

from pip2nix import resources
from pip2nix.cli import generate
from pip2nix.config import MERGED_CLI_OPTIONS, Config


# What reads each key `confspec.ini` declares, named down to the
# function so that naming one is a claim rather than a gesture. A key
# with no reader is the defect this repository keeps producing --
# `--no-binary`, `-e` and the `[[package]]` section were each found by
# accident rather than by looking.
KEY_READERS = {
    'requirements': 'pip2nix.config:Config.get_requirements',
    'constraints': 'pip2nix.config:Config.get_constraints',
    'index_url': 'pip2nix.config:Config.get_indexes',
    'extra_index_url': 'pip2nix.config:Config.get_indexes',
    'no_index': 'pip2nix.config:Config.get_indexes',
    'only_direct': 'pip2nix.report:resolve_packages',
    'excluded_packages': 'pip2nix.report:resolve_packages',
    'output': 'pip2nix.cli:generate',
    'licenses': 'pip2nix.cli:generate',
}


FILE_VALUES = {
    'output': './generated.nix',
    'index_url': 'https://mirror.example/simple',
    'extra_index_url': ['https://internal.example/simple',
                        'https://vendor.example/simple'],
    'no_index': True,
    'only_direct': True,
    'licenses': True,
}


def test_the_fixture_covers_every_shared_option():
    assert set(FILE_VALUES) == set(MERGED_CLI_OPTIONS)


def test_every_shared_option_can_be_set_in_a_configuration_file(monkeypatch):
    config = configuration_from_a_file_alone(monkeypatch)

    assert {key: config['pip2nix'][key] for key in FILE_VALUES} == FILE_VALUES


def test_every_declared_key_is_named_by_a_reader():
    assert set(declared_keys()) == set(KEY_READERS)


@pytest.mark.parametrize('key,reader', sorted(KEY_READERS.items()))
def test_the_named_reader_reads_the_key(key, reader):
    source = source_of(reader)

    assert '"{}"'.format(key) in source or "'{}'".format(key) in source


@pytest.mark.parametrize('key', [
    'requirements', 'constraints', 'excluded_packages', 'extra_index_url'])
def test_a_list_option_takes_a_single_value(key):
    config = Config()
    config.merge_options({'pip2nix': {'requirements': ['.'], key: 'one'}})

    config.validate()

    assert config['pip2nix'][key] == ['one']


def declared_keys():
    spec = configobj.ConfigObj(
        {}, configspec=io.StringIO(resources.read_text('confspec.ini')))
    return spec.configspec['pip2nix'].scalars


def source_of(reader):
    """
    The source of a `module:attribute.path` reader.

    A click command is a `Command` wrapping the function it decorates,
    which carries the source and hangs off it as `callback`.
    """
    module_name, _, attributes = reader.partition(':')
    target = importlib.import_module(module_name)
    for attribute in attributes.split('.'):
        target = getattr(target, attribute)
    return inspect.getsource(getattr(target, 'callback', target))


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
