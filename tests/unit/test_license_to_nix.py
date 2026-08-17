import pytest

from pip2nix.models.license import license_to_nix


@pytest.fixture
def known_licenses(mocker):
    """
    Stands in for the `nixpkgs.lib.licenses` lookup, which needs nix.
    """
    known = {
        "GPL-3.0-or-later": "gpl3Plus",
        "MIT": "mit",
        "MIT License": "mit",
    }
    mocker.patch(
        "pip2nix.models.license.nix_license_attribute",
        side_effect=known.get,
    )


def test_renders_nothing_when_no_license_is_declared(known_licenses):
    assert license_to_nix([]) is None


def test_renders_a_license_nixpkgs_knows(known_licenses):
    assert license_to_nix(["GPL-3.0-or-later"]) == "[ pkgs.lib.licenses.gpl3Plus ]"


def test_renders_only_the_spellings_nixpkgs_knows(known_licenses):
    assert license_to_nix(["Frobnicate 1.0", "MIT"]) == "[ pkgs.lib.licenses.mit ]"


def test_renders_each_license_once(known_licenses):
    assert license_to_nix(["MIT", "MIT License"]) == "[ pkgs.lib.licenses.mit ]"


def test_renders_the_first_license_by_name_when_nixpkgs_knows_none(known_licenses):
    assert (
        license_to_nix(["Frobnicate 1.0", "Frobnicate 2.0"])
        == '[ { fullName = "Frobnicate 1.0"; } ]'
    )
