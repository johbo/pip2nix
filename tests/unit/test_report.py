import json
import os
import subprocess
from textwrap import dedent

import pytest
from packaging.version import Version

from pip2nix import report as report_module
from pip2nix.config import Config
from pip2nix.models import package
from pip2nix.models.package import PYPROJECT, SETUPTOOLS, WHEEL
from pip2nix.models.source import Source
from pip2nix.report import (
    MINIMUM_PIP_VERSION,
    ReportError,
    build_pip_argv,
    build_source_pip_argv,
    check_pip_version,
    needs_source_distribution,
    packages_from_report,
    parse_pip_version,
    read_build_systems,
    resolve_source_distributions,
    source_distribution_of,
)


FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')

PYTHON = '/nix/store/stub-python/bin/python'

ENVIRONMENT = {'sys_platform': 'linux', 'python_version': '3.13'}


@pytest.fixture
def report():
    return load_report('report-single-wheel.json')


@pytest.fixture
def trytond_report():
    """
    A real report for `trytond_account` as pip wrote it. It carries
    extras, markers and names that are not canonical.
    """
    return load_report('report-trytond-account.json')


@pytest.fixture
def git_report():
    """
    A real report for `six` installed from its git repository, captured
    by `fixtures/capture-reports.sh`.
    """
    return load_report('report-git.json')


@pytest.fixture
def binary_wheel_report():
    """
    A real report for `asyncpg`, which pip resolves to a manylinux wheel
    that Nix cannot build from.
    """
    return load_report('report-binary-wheel.json')


@pytest.fixture
def sdist_report():
    """
    The same requirement resolved once the wheel is refused, which is
    what the substitution of ADR-0003 takes its source from.
    """
    return load_report('report-binary-wheel-sdist.json')


@pytest.fixture
def setuptools_report():
    """
    A real report for `zc.lockfile`, which declares `setuptools` at
    runtime, so the resolution carries it as a package and as an edge.
    """
    return load_report('report-setuptools.json')


@pytest.fixture
def source_passes(monkeypatch):
    """
    Answers every pass with the source distribution of the package it
    pins, and records the argv each one was asked with.
    """
    passes = []

    def read_report(argv):
        passes.append(argv)
        name, version = argv[-1].split('==')
        return one_package_report(
            name, version, '{}-{}.tar.gz'.format(name, version))

    monkeypatch.setattr('pip2nix.report._read_report', read_report)
    return passes


def load_report(name):
    with open(os.path.join(FIXTURES, name)) as f:
        return json.load(f)


def one_package_report(name, version, filename):
    return {
        'version': '1',
        'environment': ENVIRONMENT,
        'install': [{
            'requested': True,
            'metadata': {'name': name, 'version': version},
            'download_info': {
                'url': 'https://index.example/packages/' + filename,
                'archive_info': {'hashes': {'sha256': 'ff' * 32}},
            },
        }],
    }


def maturin_report():
    """
    maturin as pip resolves it, which is the case ADR-0005 turns on: it
    is emitted as a package and builds two others in the same run.
    """
    return one_package_report(
        'maturin', '1.14.1',
        'maturin-1.14.1-py3-none-manylinux_2_12_x86_64.whl')


def package_named(packages, name):
    return next(package for package in packages if package.name == name)


def make_config(requirements, **options):
    config = Config()
    config.merge_options(
        {'pip2nix': dict(options, requirements=requirements)})
    config.validate()
    return config


def test_renders_a_wheel_from_the_report(report):
    packages = read_build_systems(packages_from_report(report), ENVIRONMENT)

    assert len(packages) == 1
    assert packages[0].to_nix(include_lic=False) == dedent('''\
        super.buildPythonPackage rec {
          pname = "certifi";
          version = "2026.1.1";
          src = fetchurl {
            url = "https://index.example/packages/certifi-2026.1.1-py3-none-any.whl";
            sha256 = "04mmsvw5c0ps2gh6hqwkcs5gyyvmfpr32zvxmv3w68a2mn5kwm39";
          };
          format = "wheel";
          doCheck = false;
          buildInputs = [];
          checkInputs = [];
          nativeBuildInputs = [];
          propagatedBuildInputs = [];
        };''')


def test_names_a_package_canonically(report):
    report['install'][0]['metadata']['name'] = 'Trytond_Account'

    assert packages_from_report(report)[0].name == 'trytond-account'


def test_reads_the_dependencies_of_a_package(trytond_report):
    expected = [
        ('python-dateutil', '2.9.0.post0'),
        ('python-sql', '1.8.1'),
        ('simpleeval', '1.0.7'),
        ('trytond', '7.0.55'),
        ('trytond-company', '7.0.4'),
        ('trytond-currency', '7.0.1'),
        ('trytond-party', '7.0.7'),
    ]

    packages = packages_from_report(trytond_report)

    assert package_named(packages, 'trytond-account').dependencies == expected


def test_renders_a_dependency_an_extra_pulled_in(trytond_report):
    expected = dedent('''\
        propagatedBuildInputs = [
            self."genshi"
            self."lxml"
            self."puremagic"
          ];''')

    packages = packages_from_report(trytond_report)

    assert expected in package_named(packages, 'relatorio').to_nix(
        include_lic=False)


def test_reads_no_dependencies_when_every_requirement_is_extra_gated(
        trytond_report):
    packages = packages_from_report(trytond_report)

    assert package_named(packages, 'lxml').dependencies == []


def test_emits_only_the_requested_packages(trytond_report):
    packages = packages_from_report(trytond_report, only_direct=True)

    assert [package.name for package in packages] == ['trytond-account']


def test_keeps_the_dependencies_on_packages_it_does_not_emit(trytond_report):
    expected = ['python-dateutil', 'python-sql', 'simpleeval', 'trytond',
                'trytond-company', 'trytond-currency', 'trytond-party']

    packages = packages_from_report(trytond_report, only_direct=True)

    package = package_named(packages, 'trytond-account')
    assert [name for name, _version in package.dependencies] == expected


def test_emits_every_resolved_package_by_default(trytond_report):
    packages = packages_from_report(trytond_report)

    assert len(packages) == len(trytond_report['install'])


def test_omits_an_excluded_package(setuptools_report):
    packages = packages_from_report(setuptools_report,
                                    excluded=['setuptools'])

    assert [package.name for package in packages] == ['zc-lockfile']


def test_drops_the_edges_to_an_excluded_package(setuptools_report):
    packages = packages_from_report(setuptools_report,
                                    excluded=['setuptools'])

    assert package_named(packages, 'zc-lockfile').dependencies == []


@pytest.mark.parametrize('spelling', ['zc.lockfile', 'ZC_Lockfile'])
def test_matches_an_excluded_name_canonically(setuptools_report, spelling):
    packages = packages_from_report(setuptools_report, excluded=[spelling])

    assert [package.name for package in packages] == ['setuptools']


def test_omits_an_excluded_package_that_was_requested(setuptools_report):
    packages = packages_from_report(setuptools_report, only_direct=True,
                                    excluded=['zc.lockfile'])

    assert packages == []


@pytest.mark.parametrize('filename, needed', [
    ('certifi-2026.1.1-py3-none-any.whl', False),
    ('certifi-2026.1.1-py2.py3-none-any.whl', False),
    ('asyncpg-0.30.0-cp313-cp313-manylinux_2_17_x86_64.whl', True),
    ('certifi-2026.1.1.tar.gz', False),
    ('certifi-2026.1.1.zip', False),
    ('certifi-2026.1.1-py3.13.egg', True),
])
def test_which_sources_nix_cannot_build_from(filename, needed):
    source = Source.from_url('https://index.example/packages/' + filename)

    assert needs_source_distribution(source) is needed


def test_takes_the_source_distribution_of_a_binary_wheel(
        binary_wheel_report, sdist_report):
    package = packages_from_report(binary_wheel_report)[0]

    source = source_distribution_of(package, sdist_report)

    assert source.url.endswith('asyncpg-0.30.0.tar.gz')


def test_pins_the_substituted_source_to_its_own_hash(
        binary_wheel_report, sdist_report):
    expected = sdist_report['install'][0]['download_info'][
        'archive_info']['hashes']['sha256']
    package = packages_from_report(binary_wheel_report)[0]

    assert source_distribution_of(package, sdist_report).sha256 == expected


def test_rejects_a_source_distribution_of_another_version(
        binary_wheel_report, sdist_report):
    sdist_report['install'][0]['metadata']['version'] = '0.31.0'
    package = packages_from_report(binary_wheel_report)[0]

    with pytest.raises(ReportError):
        source_distribution_of(package, sdist_report)


def test_rejects_a_pass_that_lost_the_package(
        binary_wheel_report, sdist_report):
    sdist_report['install'] = []
    package = packages_from_report(binary_wheel_report)[0]

    with pytest.raises(ReportError):
        source_distribution_of(package, sdist_report)


def test_starts_no_pass_when_every_wheel_is_pure(report, source_passes):
    packages = packages_from_report(report)

    resolve_source_distributions(packages, make_config(['certifi']), PYTHON)

    assert source_passes == []
    assert packages[0].source.url.endswith('-py3-none-any.whl')


def test_starts_one_pass_for_a_binary_wheel(binary_wheel_report,
                                            source_passes):
    packages = packages_from_report(binary_wheel_report)

    resolve_source_distributions(packages, make_config(['asyncpg']), PYTHON)

    assert [argv[-1] for argv in source_passes] == ['asyncpg==0.30.0']
    assert packages[0].source.url.endswith('asyncpg-0.30.0.tar.gz')


def test_names_one_package_per_pass(binary_wheel_report, report,
                                    source_passes):
    """
    The defect ADR-0005 removes: a pass naming several packages refuses
    a wheel to one that another one is built with.
    """
    packages = (packages_from_report(binary_wheel_report)
                + packages_from_report(maturin_report())
                + packages_from_report(report))

    resolve_source_distributions(packages, make_config(['asyncpg']), PYTHON)

    assert [argv[argv.index('--no-binary') + 1] for argv in source_passes] == [
        'asyncpg', 'maturin']
    assert [package.source.url.rsplit('/', 1)[-1] for package in packages] == [
        'asyncpg-0.30.0.tar.gz',
        'maturin-1.14.1.tar.gz',
        'certifi-2026.1.1-py3-none-any.whl',
    ]


def test_reads_the_build_system_of_a_source(report, tmp_path):
    (tmp_path / 'pyproject.toml').write_text(
        '[build-system]\nrequires = ["hatchling"]\n')
    report['install'][0]['download_info'] = {
        'url': 'file://{}'.format(tmp_path),
        'dir_info': {},
    }
    packages = packages_from_report(report)

    read_build_systems(packages, ENVIRONMENT)

    assert packages[0].setup_requires == ['hatchling']
    assert packages[0].format == PYPROJECT


def test_reads_no_build_system_for_a_wheel(report):
    packages = packages_from_report(report)

    read_build_systems(packages, ENVIRONMENT)

    assert packages[0].setup_requires == []
    assert packages[0].format == WHEEL


def test_builds_a_source_without_a_build_system_the_legacy_way(
        report, tmp_path):
    (tmp_path / 'setup.py').write_text('')
    report['install'][0]['download_info'] = {
        'url': 'file://{}'.format(tmp_path),
        'dir_info': {},
    }
    packages = packages_from_report(report)

    read_build_systems(packages, ENVIRONMENT)

    assert packages[0].setup_requires == []
    assert packages[0].format == SETUPTOOLS


def test_reads_the_build_system_of_a_git_checkout(
        git_report, monkeypatch, tmp_path):
    (tmp_path / 'pyproject.toml').write_text(
        '[build-system]\nrequires = ["setuptools"]\n')
    monkeypatch.setattr(
        'pip2nix.report.prefetch_git',
        lambda url, rev: ('the-content-hash', rev, str(tmp_path)))
    packages = packages_from_report(git_report)

    read_build_systems(packages, ENVIRONMENT)

    assert packages[0].setup_requires == ['setuptools']
    assert packages[0].format == PYPROJECT


def test_asks_pip_for_the_source_of_one_package():
    package = packages_from_report(maturin_report())[0]

    argv = build_source_pip_argv(PYTHON, make_config(['maturin']), package)

    assert argv == [
        PYTHON, '-m', 'pip', 'install',
        '--dry-run',
        '--ignore-installed',
        '--quiet',
        '--index-url', 'https://pypi.python.org/simple',
        '--no-deps',
        '--no-binary', 'maturin',
        'maturin==1.14.1',
    ]


def test_asks_for_no_requirement_but_the_pinned_one():
    """
    A pass carrying the configured requirements would resolve the whole
    set again, and every package it named would be refused a wheel.
    """
    config = make_config(['-r requirements.txt'],
                         constraints=['constraints.txt'])
    package = packages_from_report(maturin_report())[0]

    argv = build_source_pip_argv(PYTHON, config, package)

    assert '--requirement' not in argv
    assert '--constraint' not in argv


def test_carries_the_indexes_into_a_source_pass():
    config = make_config(['maturin'],
                         index_url='https://index.example/simple',
                         extra_index_url=['https://extra.example/simple'])
    package = packages_from_report(maturin_report())[0]

    argv = build_source_pip_argv(PYTHON, config, package)

    assert argv[argv.index('--index-url') + 1] == 'https://index.example/simple'
    assert argv[argv.index('--extra-index-url') + 1] == (
        'https://extra.example/simple')


def test_disables_the_index_in_a_source_pass_as_well():
    config = make_config(['maturin'], no_index=True)
    package = packages_from_report(maturin_report())[0]

    argv = build_source_pip_argv(PYTHON, config, package)

    assert '--no-index' in argv
    assert '--index-url' not in argv


def test_reads_the_license_and_the_classifier(trytond_report):
    expected = ['GPL-3', 'GNU General Public License v3 or later (GPLv3+)']

    packages = packages_from_report(trytond_report)

    assert package_named(packages, 'trytond-account').licenses == expected


def test_reads_the_spdx_expression_of_a_package_that_declares_one(
        trytond_report):
    packages = packages_from_report(trytond_report)

    assert package_named(packages, 'relatorio').licenses == [
        'GPL-3.0-or-later']


def test_orders_the_licenses_with_the_spdx_expression_first(report):
    metadata = report['install'][0]['metadata']
    metadata['license_expression'] = 'Apache-2.0'
    metadata['license'] = 'Apache 2.0'
    metadata['classifier'] = [
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
    ]

    assert packages_from_report(report)[0].licenses == [
        'Apache-2.0', 'Apache 2.0', 'Apache Software License']


def test_reads_no_license_from_metadata_that_declares_none(report):
    assert packages_from_report(report)[0].licenses == []


def test_drops_the_placeholder_setuptools_wrote_for_no_license(report):
    report['install'][0]['metadata']['license'] = 'UNKNOWN'

    assert packages_from_report(report)[0].licenses == []


def test_rejects_an_unknown_report_version(report):
    report['version'] = '2'

    with pytest.raises(ReportError):
        packages_from_report(report)


def test_rejects_a_source_without_a_sha256(report):
    del report['install'][0]['download_info']['archive_info']['hashes']

    with pytest.raises(ReportError):
        packages_from_report(report)


def test_renders_a_git_source(git_report, monkeypatch):
    monkeypatch.setattr(
        package, 'prefetch_git',
        lambda url, rev: ('the-content-hash', rev, '/store/repo'))

    packages = packages_from_report(git_report)

    assert packages[0].to_nix(include_lic=False) == dedent('''\
        super.buildPythonPackage rec {
          pname = "six";
          version = "1.16.0";
          src = fetchgit {
            url = "https://github.com/benjaminp/six";
            rev = "65486e4383f9f411da95937451205d3c7b61b9e1";
            sha256 = "the-content-hash";
          };
          format = "setuptools";
          doCheck = false;
          buildInputs = [];
          checkInputs = [];
          nativeBuildInputs = [];
          propagatedBuildInputs = [];
        };''')


def test_rejects_a_mercurial_source(git_report):
    git_report['install'][0]['download_info']['vcs_info']['vcs'] = 'hg'

    with pytest.raises(ReportError):
        packages_from_report(git_report)


def test_rejects_an_editable_requirement_from_a_requirements_file(
        report, tmpdir):
    report['install'][0]['download_info'] = {
        'url': 'file://{}/src/certifi'.format(tmpdir),
        'dir_info': {'editable': True},
    }

    with pytest.raises(ReportError):
        packages_from_report(report)


def test_renders_a_local_directory_without_a_hash(report, tmpdir):
    report['install'][0]['download_info'] = {
        'url': 'file://{}'.format(tmpdir),
        'dir_info': {},
    }

    package = packages_from_report(report)[0]

    assert package.source.sha256 is None


def test_reads_the_version_pip_prints():
    output = 'pip 25.3 from /nix/store/stub/pip (python 3.13)\n'

    assert parse_pip_version(output) == Version('25.3')


def test_rejects_a_pip_that_cannot_write_a_report(monkeypatch):
    monkeypatch.setattr(
        subprocess, 'check_output',
        lambda argv: b'pip 21.3.1 from /nix/store/stub/pip (python 3.9)\n')

    with pytest.raises(ReportError) as error:
        check_pip_version(PYTHON)

    assert '21.3.1' in str(error.value)
    assert MINIMUM_PIP_VERSION in str(error.value)


def test_rejects_output_that_carries_no_version(monkeypatch):
    monkeypatch.setattr(subprocess, 'check_output', lambda argv: b'')

    with pytest.raises(ReportError):
        check_pip_version(PYTHON)


def test_asks_pip_to_resolve_the_requirements():
    config = make_config(['certifi'])

    argv = build_pip_argv(PYTHON, config)

    assert argv == [
        PYTHON, '-m', 'pip', 'install',
        '--dry-run',
        '--ignore-installed',
        '--quiet',
        '--index-url', 'https://pypi.python.org/simple',
        'certifi',
    ]


def test_passes_each_requirement_as_its_own_argument():
    config = make_config(['certifi', 'idna >= 2.5, < 4'])

    argv = build_pip_argv(PYTHON, config)

    assert argv[-2:] == ['certifi', 'idna >= 2.5, < 4']


def test_passes_requirements_files_and_constraints():
    config = make_config(['-r requirements.txt'],
                         constraints=['constraints.txt'])

    argv = build_pip_argv(PYTHON, config)

    assert argv[-4:] == ['--constraint', 'constraints.txt',
                         '--requirement', 'requirements.txt']


def test_passes_the_indexes():
    config = make_config(['certifi'],
                         index_url='https://index.example/simple',
                         extra_index_url=['https://extra.example/simple'])

    argv = build_pip_argv(PYTHON, config)

    assert '--index-url' in argv
    assert argv[argv.index('--index-url') + 1] == 'https://index.example/simple'
    assert argv[argv.index('--extra-index-url') + 1] == (
        'https://extra.example/simple')


def test_disables_the_index_when_configured():
    config = make_config(['certifi'], no_index=True)

    argv = build_pip_argv(PYTHON, config)

    assert '--no-index' in argv
    assert '--index-url' not in argv


def test_reads_the_report_pip_wrote_where_it_was_asked_to(monkeypatch):
    """
    Nothing else knows the path: it lives for one pass, in a temporary
    directory the reader owns.
    """
    written = {'version': '1', 'install': []}
    asked = []

    def check_call(argv):
        asked.append(argv)
        with open(argv[argv.index('--report') + 1], 'w') as f:
            json.dump(written, f)

    monkeypatch.setattr('pip2nix.report.subprocess.check_call', check_call)

    assert report_module._read_report([PYTHON, '-m', 'pip']) == written
    assert asked[0][:3] == [PYTHON, '-m', 'pip']


def test_rejects_an_editable_requirement():
    config = make_config(['-e .'])

    with pytest.raises(ReportError):
        build_pip_argv(PYTHON, config)
