from textwrap import dedent

from pip2nix.models.package import PythonPackage
from pip2nix.models.source import Source


WHEEL_URL = 'https://index.example/packages/certifi-2026.1.1-py3-none-any.whl'
SDIST_URL = 'https://index.example/packages/certifi-2026.1.1.tar.gz'
ZIP_URL = 'https://index.example/packages/certifi-2026.1.1.zip'

# `nix hash convert --hash-algo sha256 --to nix32` agrees on this pair.
SHA256_HEX = '69543e8bad4221c3c7ae7d7f31f275757bff8a66936368e013fa0256f8d6b512'


def make_package(url):
    return PythonPackage(
        name='certifi',
        version='2026.1.1',
        dependencies=[],
        source=Source.from_url(url, sha256=SHA256_HEX),
    )


def test_renders_a_wheel():
    assert make_package(WHEEL_URL).to_nix(include_lic=False) == dedent('''\
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


def test_renders_an_sdist_as_a_setuptools_build():
    assert 'format = "setuptools";' in make_package(SDIST_URL).to_nix(
        include_lic=False)


def test_renders_unzip_for_a_zip_source():
    assert ('nativeBuildInputs = [\n    pkgs."unzip"\n  ];'
            in make_package(ZIP_URL).to_nix(include_lic=False))
