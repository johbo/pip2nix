import json
from subprocess import check_output

import pytest

from pip2nix.models.license import license_to_nix


pytestmark = pytest.mark.nix

# Everything the index could declare that means something to Nix.
HOSTILE_NAME = 'Ends the "; attribute = ${pkgs.hello}; and \\ escapes'


def test_an_escaped_full_name_reaches_nix_unchanged(mocker):
    mocker.patch("pip2nix.models.license.nix_license_attribute", return_value=None)

    rendered = license_to_nix([HOSTILE_NAME], "certifi")

    evaluated = check_output(
        ["nix-instantiate", "--eval", "--strict", "--json", "--expr", rendered]
    )
    assert json.loads(evaluated) == [{"fullName": HOSTILE_NAME}]
