"""
Resolution through pip's installation report.

pip is run as a subprocess and asked for a `--report`, the documented and
versioned JSON description of what it would install. Nothing on this path
touches `pip._internal`, which is the point of ADR-0001.
"""

import json
import os
import subprocess
import tempfile
from dataclasses import replace

from packaging.utils import canonicalize_name

from .dependencies import resolve_dependencies
from .models.package import PythonPackage
from .models.source import Source


REPORT_VERSION = '1'

REMOTE_SCHEMES = ('http', 'https')


class ReportError(Exception):
    pass


def resolve_packages(config, python_executable):
    packages = packages_from_report(
        _read_report(config, python_executable),
        only_direct=config.get_config('pip2nix', 'only_direct'))
    return _resolve_source_distributions(
        packages, config, python_executable)


def packages_from_report(report, only_direct=False):
    entries = _entries_of(report)
    dependencies = resolve_dependencies(entries, report['environment'])
    if only_direct:
        entries = [entry for entry in entries if entry['requested']]
    return [_package_from_entry(entry, dependencies) for entry in entries]


def needs_source_distribution(source):
    """
    Whether Nix can build from the file pip resolved to.

    A wheel built for a platform links against libraries at paths that
    do not exist in the store, so ADR-0003 replaces it with the
    project's sdist. A `-any` wheel carries the same modules its sdist
    does and is left alone.
    """
    return source.path.endswith('.egg') or (
        source.path.endswith('.whl')
        and not source.path.endswith('-any.whl'))


def substitute_source_distributions(packages, report):
    """
    Take the sources of a `--no-binary` resolution for the packages that
    need one, leaving the rest of the package as the first report
    described it.
    """
    entries = {canonicalize_name(entry['metadata']['name']): entry
               for entry in _entries_of(report)}
    for package in packages:
        if needs_source_distribution(package.source):
            package.source = _source_distribution_of(package, entries)
    return packages


def build_pip_argv(python_executable, config, report_path, no_binary=()):
    argv = [
        python_executable, '-m', 'pip', 'install',
        '--dry-run',
        '--ignore-installed',
        '--quiet',
        '--report', report_path,
    ]

    indexes = config.get_indexes()
    if indexes:
        argv += ['--index-url', indexes[0]]
        for extra_index in indexes[1:]:
            argv += ['--extra-index-url', extra_index]
    else:
        argv.append('--no-index')

    for constraint in config.get_constraints():
        argv += ['--constraint', constraint]

    if no_binary:
        argv += ['--no-binary', ','.join(no_binary)]

    for kind, requirement in config.get_requirements():
        if kind == '-r':
            argv += ['--requirement', requirement]
        elif kind == '-e':
            raise ReportError(
                'Editable requirements are not supported: "{}". The report '
                'describes them as a local directory, which loses the url '
                'and the revision they were installed from.'.format(
                    requirement))
        else:
            argv.append(requirement)

    return argv


def _entries_of(report):
    version = report.get('version')
    if version != REPORT_VERSION:
        raise ReportError(
            'Cannot read an installation report of version "{}", '
            'pip2nix understands version "{}".'.format(
                version, REPORT_VERSION))
    return report['install']


def _resolve_source_distributions(packages, config, python_executable):
    no_binary = [package.name for package in packages
                 if needs_source_distribution(package.source)]
    if not no_binary:
        return packages
    return substitute_source_distributions(
        packages, _read_report(config, python_executable, no_binary))


def _source_distribution_of(package, entries):
    try:
        entry = entries[package.name]
    except KeyError:
        raise ReportError(
            'Resolving "{}" from its source distribution did not produce '
            'it at all.'.format(package.name))
    if entry['metadata']['version'] != package.version:
        raise ReportError(
            'Resolving "{name}" from its source distribution produced '
            'version {sdist} where the wheel resolved to {wheel}. Refusing '
            'to pin a source the rendered metadata does not describe.'.format(
                name=package.name,
                sdist=entry['metadata']['version'],
                wheel=package.version))
    return _source_from_download_info(entry['download_info'])


def _read_report(config, python_executable, no_binary=()):
    with tempfile.TemporaryDirectory(prefix='pip2nix-') as directory:
        report_path = os.path.join(directory, 'report.json')
        argv = build_pip_argv(
            python_executable, config, report_path, no_binary)
        try:
            subprocess.check_call(argv)
        except subprocess.CalledProcessError as error:
            raise ReportError(
                'pip could not resolve the requirements, it exited with '
                'status {}.'.format(error.returncode))
        with open(report_path) as report_file:
            return json.load(report_file)


def _package_from_entry(entry, dependencies):
    metadata = entry['metadata']
    name = canonicalize_name(metadata['name'])
    return PythonPackage(
        name=name,
        version=metadata['version'],
        dependencies=dependencies[name],
        source=_source_from_download_info(entry['download_info']),
    )


def _source_from_download_info(download_info):
    url = download_info['url']
    if 'vcs_info' in download_info:
        return _repository_source(url, download_info['vcs_info'])
    if download_info.get('dir_info', {}).get('editable'):
        raise ReportError(
            'Cannot generate a source for "{}": the report describes an '
            'editable requirement as the local directory it would be '
            'checked out into, which loses the url and the revision it '
            'comes from.'.format(url))

    source = Source.from_url(url)
    if source.scheme in REMOTE_SCHEMES:
        return replace(source, sha256=_sha256_of(download_info))
    return source


def _repository_source(url, vcs_info):
    vcs = vcs_info['vcs']
    if vcs != 'git':
        raise ReportError(
            'Cannot generate a source for "{url}": pip2nix renders git '
            'repositories, this one is {vcs}.'.format(url=url, vcs=vcs))
    return replace(Source.from_url(url), vcs=vcs, rev=vcs_info['commit_id'])


def _sha256_of(download_info):
    hashes = download_info.get('archive_info', {}).get('hashes', {})
    try:
        return hashes['sha256']
    except KeyError:
        raise ReportError(
            'The index published no sha256 for "{}". Refusing to generate '
            'a source without a hash to pin it.'.format(download_info['url']))
