import os
import sys

import click
import jinja2
import pkg_resources
from packaging.utils import canonicalize_name

import pip2nix

from .config import Config
from .output import write_output
from .report import ReportError, resolve_packages


@click.group()
def cli():
    pass


@cli.command()
@click.option('--output', metavar='<path>',
              help="Write the generated nix to <path>.")
@click.option('--only-direct', is_flag=True, default=None,
              help="Only render direct dependencies.")
@click.option('--index-url', '-i', metavar='<url>',
              help="Base URL of Python Package Index.")
@click.option('--extra-index-url', multiple=True, metavar='<url>',
              help="Extra index URLs to use.")
@click.option('--no-index/--index',
              help="Ignore indexes.")
@click.option('--configuration', metavar='<path>',
              help="Read pip2nix configuration from <path>.")
@click.option('--editable', '-e', multiple=True, type=click.Path(),
              metavar='<spec>',
              help="Add an editable requirement, which pip2nix refuses "
                   "to render.")
@click.option('--requirement', '-r', multiple=True, type=click.Path(),
              metavar='<file>',
              help="Load specifiers from a requirements file.")
@click.option('--constraint', '-c', multiple=True, type=click.Path(),
              metavar='<file>',
              help="Constrain versions based on the constraints file.")
@click.option('--licenses/--no-licenses', default=False,
              help="Extract license information as well, off by default.")
@click.argument('specifiers', nargs=-1)
def generate(specifiers, **kwargs):
    """Generate a .nix file with specified packages."""
    kwargs['specifiers'] = specifiers
    kwargs['editables'] = kwargs.pop('editable', ())
    kwargs['requirements'] = kwargs.pop('requirement', None)
    kwargs['constraints'] = kwargs.pop('constraint', None)

    config = Config()
    if kwargs['configuration']:
        config.load(kwargs['configuration'])
    else:
        config.find_and_load()
    config.merge_cli_options(kwargs)
    config.validate()

    python_executable = (
        os.environ.get('PIP2NIX_PYTHON_EXECUTABLE') or sys.executable)
    try:
        packages = resolve_packages(config, python_executable)
    except ReportError as error:
        raise click.ClickException(str(error))

    write_output(
        config['pip2nix']['output'],
        packages,
        config['pip2nix']['licenses'])


@cli.command()
@click.option('--configuration', metavar='<path>',
              help="Read pip2nix configuration from <path>.")
@click.option('--output', metavar='<path>', default='default.nix',
              help="Write the generated file to <path>.")
@click.option('--overrides-output', metavar='<path>',
              default='python-packages-overrides.nix',
              help="Write the generated overrides file to <path>.")
@click.option('--package', metavar='<package>',
              required=True,
              help="Name of the package the scaffold is for.")
def scaffold(output, overrides_output, **kwargs):
    config = Config()
    if kwargs['configuration']:
        config.load(kwargs['configuration'])
    else:
        config.find_and_load()
    config.merge_cli_options(kwargs)
    # TODO: Config enforces requirements to be specified, find a nicer
    # way to let Config know that we don't need requirements here.
    config.merge_options({'pip2nix': {'requirements': []}})
    config.validate()

    write_template(
        'default.nix.j2', output,
        package_name=canonicalize_name(kwargs['package']))
    write_template(
        'python-packages-overrides.nix.j2', overrides_output)


def write_template(template_name, output, **context):
    template = pkg_resources.resource_string(__name__, template_name)
    rendered = jinja2.Template(template.decode('utf-8')).render(
        pip2nix_version=pip2nix.__version__, **context)
    with open(output, 'w') as f:
        f.write(rendered)
