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
    return packages_from_report(
        _read_report(config, python_executable),
        only_direct=config.get_config('pip2nix', 'only_direct'))


def packages_from_report(report, only_direct=False):
    version = report.get('version')
    if version != REPORT_VERSION:
        raise ReportError(
            'Cannot read an installation report of version "{}", '
            'pip2nix understands version "{}".'.format(
                version, REPORT_VERSION))
    entries = report['install']
    dependencies = resolve_dependencies(entries, report['environment'])
    if only_direct:
        entries = [entry for entry in entries if entry['requested']]
    return [_package_from_entry(entry, dependencies) for entry in entries]


def build_pip_argv(python_executable, config, report_path):
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


def _read_report(config, python_executable):
    with tempfile.TemporaryDirectory(prefix='pip2nix-') as directory:
        report_path = os.path.join(directory, 'report.json')
        argv = build_pip_argv(python_executable, config, report_path)
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
