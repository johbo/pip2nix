import pytest

from pip2nix import licenses


pytestmark = pytest.mark.nix


def test_get_nix_licenses():
    known = licenses.get_nix_licenses()

    assert 'gpl3' in known
