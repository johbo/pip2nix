from textwrap import dedent

from pip2nix.models.package import PythonPackage
from pip2nix.models.source import Source

from .digests import SHA256_HEX


WHEEL_URL = 'https://index.example/packages/certifi-2026.1.1-py3-none-any.whl'
SDIST_URL = 'https://index.example/packages/certifi-2026.1.1.tar.gz'
ZIP_URL = 'https://index.example/packages/certifi-2026.1.1.zip'


def make_package(url, dependencies=()):
    return PythonPackage(
        name='certifi',
        version='2026.1.1',
        dependencies=list(dependencies),
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


def test_renders_dependencies_as_propagated_build_inputs():
    expected = dedent('''\
        propagatedBuildInputs = [
            self."idna"
            self."urllib3"
          ];''')

    package = make_package(WHEEL_URL,
                           dependencies=[('idna', '3.18'), ('urllib3', '2.7.0')])

    assert expected in package.to_nix(include_lic=False)


def test_renders_unzip_for_a_zip_source():
    assert ('nativeBuildInputs = [\n    pkgs."unzip"\n  ];'
            in make_package(ZIP_URL).to_nix(include_lic=False))
