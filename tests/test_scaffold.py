import shutil
import subprocess
import textwrap

import pytest
from click.testing import CliRunner

from pip2nix.cli import scaffold


def stub_package_set(name):
    return textwrap.dedent('''\
        { pkgs, fetchurl, fetchgit, fetchhg }:

        self: super: {
          "PACKAGE" = super.buildPythonPackage {
            pname = "PACKAGE";
            version = "1.0";
            src = ./.;
            format = "setuptools";
          };
        }
    ''').replace('PACKAGE', name)


def run_scaffold(tmp_path, monkeypatch, package):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(scaffold, ['--package', package])
    assert result.exit_code == 0, result.output
    return tmp_path / 'default.nix'


@pytest.mark.skipif(
    shutil.which('nix-instantiate') is None,
    reason="Calling nix from inside the build does not work.")
def test_scaffolded_default_nix_evaluates(tmp_path, monkeypatch):
    default_nix = run_scaffold(tmp_path, monkeypatch, 'my-project')
    (tmp_path / 'python-packages.nix').write_text(
        stub_package_set('my-project'))

    instantiate = subprocess.run(
        ['nix-instantiate', str(default_nix)],
        capture_output=True, text=True)

    assert instantiate.returncode == 0, instantiate.stderr
