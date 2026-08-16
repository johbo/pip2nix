from textwrap import dedent

import pytest

from pip2nix.models.package import (
    PYPROJECT,
    SETUPTOOLS,
    WHEEL,
    PythonPackage,
)
from pip2nix.models.source import Source

from .digests import SHA256_HEX


WHEEL_URL = "https://index.example/packages/certifi-2026.1.1-py3-none-any.whl"
SDIST_URL = "https://index.example/packages/certifi-2026.1.1.tar.gz"
ZIP_URL = "https://index.example/packages/certifi-2026.1.1.zip"


def make_package(
    url, dependencies=(), licenses=(), setup_requires=(), format=SETUPTOOLS
):
    return PythonPackage(
        name="certifi",
        version="2026.1.1",
        dependencies=list(dependencies),
        source=Source.from_url(url, sha256=SHA256_HEX),
        licenses=list(licenses),
        setup_requires=list(setup_requires),
        format=format,
    )


@pytest.fixture
def nix_licenses(mocker):
    """
    Stands in for the `nixpkgs.lib.licenses` query, which needs nix.

    The values are lowercase, the way `get_nix_licenses` stores them.
    """
    mocker.patch(
        "pip2nix.licenses._nix_licenses",
        {
            "mit": {"spdxId": "mit", "fullName": "mit license"},
            "gpl3Plus": {
                "spdxId": "gpl-3.0-or-later",
                "fullName": "gnu general public license v3.0 or later",
            },
        },
    )


def test_renders_a_wheel():
    package = make_package(WHEEL_URL, format=WHEEL)

    assert package.to_nix(include_lic=False) == dedent("""\
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
        };""")


@pytest.mark.parametrize("format", [SETUPTOOLS, PYPROJECT, WHEEL])
def test_renders_the_format_it_was_given(format):
    package = make_package(SDIST_URL, format=format)

    assert 'format = "{}";'.format(format) in package.to_nix(include_lic=False)


def test_renders_dependencies_as_propagated_build_inputs():
    expected = dedent("""\
        propagatedBuildInputs = [
            self."idna"
            self."urllib3"
          ];""")

    package = make_package(
        WHEEL_URL, dependencies=[("idna", "3.18"), ("urllib3", "2.7.0")]
    )

    assert expected in package.to_nix(include_lic=False)


def test_renders_unzip_for_a_zip_source():
    assert 'nativeBuildInputs = [\n    pkgs."unzip"\n  ];' in make_package(
        ZIP_URL
    ).to_nix(include_lic=False)


def test_renders_build_requirements_as_native_build_inputs():
    expected = dedent("""\
        nativeBuildInputs = [
            self."setuptools"
            self."cython"
          ];""")

    package = make_package(SDIST_URL, setup_requires=["setuptools", "cython"])

    assert expected in package.to_nix(include_lic=False)


def test_renders_unzip_next_to_the_build_requirements():
    expected = dedent("""\
        nativeBuildInputs = [
            pkgs."unzip"
            self."setuptools"
          ];""")

    package = make_package(ZIP_URL, setup_requires=["setuptools"])

    assert expected in package.to_nix(include_lic=False)


def test_renders_a_license_from_its_spdx_identifier(nix_licenses):
    expected = dedent("""\
        meta = {
            license = [ pkgs.lib.licenses.gpl3Plus ];
          };""")

    package = make_package(WHEEL_URL, licenses=["GPL-3.0-or-later"])

    assert expected in package.to_nix(include_lic=True)


def test_renders_a_license_the_hand_written_map_knows():
    package = make_package(WHEEL_URL, licenses=["GPLv3"])

    assert "license = [ pkgs.lib.licenses.gpl3 ];" in package.to_nix(include_lic=True)


def test_renders_only_the_spellings_nixpkgs_knows(nix_licenses):
    package = make_package(WHEEL_URL, licenses=["Frobnicate 1.0", "GPLv3"])

    assert "license = [ pkgs.lib.licenses.gpl3 ];" in package.to_nix(include_lic=True)


def test_renders_each_license_once(nix_licenses):
    package = make_package(WHEEL_URL, licenses=["MIT", "MIT License"])

    assert "license = [ pkgs.lib.licenses.mit ];" in package.to_nix(include_lic=True)


def test_renders_the_first_license_by_name_when_nixpkgs_knows_none(nix_licenses):
    package = make_package(WHEEL_URL, licenses=["Frobnicate 1.0", "Frobnicate 2.0"])

    assert 'license = [ { fullName = "Frobnicate 1.0"; } ];' in package.to_nix(
        include_lic=True
    )


def test_renders_no_meta_without_the_licenses_flag():
    package = make_package(WHEEL_URL, licenses=["GPLv3"])

    assert "meta" not in package.to_nix(include_lic=False)


def test_renders_no_meta_for_a_package_that_declares_no_license():
    assert "meta" not in make_package(WHEEL_URL).to_nix(include_lic=True)
