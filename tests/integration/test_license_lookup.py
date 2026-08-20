import pytest

from pip2nix.license_lookup import LicenseLookup


pytestmark = pytest.mark.nix


def test_asks_nixpkgs_for_a_spelling_the_hand_written_map_lacks():
    assert LicenseLookup().attribute_for("GPL-3.0-or-later") == "gpl3Plus"
