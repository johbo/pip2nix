import json
import os
from textwrap import dedent

import pytest

from pip2nix.config import Config
from pip2nix.models import package
from pip2nix.report import ReportError, build_pip_argv, packages_from_report


FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')

PYTHON = '/nix/store/stub-python/bin/python'


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


def load_report(name):
    with open(os.path.join(FIXTURES, name)) as f:
        return json.load(f)


def package_named(packages, name):
    return next(package for package in packages if package.name == name)


def make_config(requirements, **options):
    config = Config()
    config.merge_options(
        {'pip2nix': dict(options, requirements=requirements)})
    config.validate()
    return config


def test_renders_a_wheel_from_the_report(report):
    packages = packages_from_report(report)

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
        package, 'prefetch_git', lambda url, rev: ('the-content-hash', rev))

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


def test_asks_pip_for_a_report():
    config = make_config(['certifi'])

    argv = build_pip_argv(PYTHON, config, '/tmp/stub/report.json')

    assert argv == [
        PYTHON, '-m', 'pip', 'install',
        '--dry-run',
        '--ignore-installed',
        '--quiet',
        '--report', '/tmp/stub/report.json',
        '--index-url', 'https://pypi.python.org/simple',
        'certifi',
    ]


def test_passes_each_requirement_as_its_own_argument():
    config = make_config(['certifi', 'idna >= 2.5, < 4'])

    argv = build_pip_argv(PYTHON, config, '/tmp/stub/report.json')

    assert argv[-2:] == ['certifi', 'idna >= 2.5, < 4']


def test_passes_requirements_files_and_constraints():
    config = make_config(['-r requirements.txt'],
                         constraints=['constraints.txt'])

    argv = build_pip_argv(PYTHON, config, '/tmp/stub/report.json')

    assert argv[-4:] == ['--constraint', 'constraints.txt',
                         '--requirement', 'requirements.txt']


def test_passes_the_indexes():
    config = make_config(['certifi'],
                         index_url='https://index.example/simple',
                         extra_index_url=['https://extra.example/simple'])

    argv = build_pip_argv(PYTHON, config, '/tmp/stub/report.json')

    assert '--index-url' in argv
    assert argv[argv.index('--index-url') + 1] == 'https://index.example/simple'
    assert argv[argv.index('--extra-index-url') + 1] == (
        'https://extra.example/simple')


def test_disables_the_index_when_configured():
    config = make_config(['certifi'], no_index=True)

    argv = build_pip_argv(PYTHON, config, '/tmp/stub/report.json')

    assert '--no-index' in argv
    assert '--index-url' not in argv


def test_rejects_an_editable_requirement():
    config = make_config(['-e .'])

    with pytest.raises(ReportError):
        build_pip_argv(PYTHON, config, '/tmp/stub/report.json')
