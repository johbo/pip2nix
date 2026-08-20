import json
from subprocess import CalledProcessError

import pytest

from pip2nix.errors import ReportError
from pip2nix.license_lookup import LicenseLookup


NOT_IN_THE_HAND_WRITTEN_MAP = "Frobnicate 1.0"


def test_maps_a_license_the_hand_written_map_knows(mocker):
    nixpkgs_refusing_to_be_asked(mocker)

    assert LicenseLookup().attribute_for("GPLv3") == "gpl3"


def test_maps_a_license_by_its_spdx_identifier(mocker):
    nixpkgs_answering(mocker, {"gpl3Plus": {"spdxId": "gpl-3.0-or-later"}})

    assert LicenseLookup().attribute_for("GPL-3.0-or-later") == "gpl3Plus"


def test_maps_nothing_for_a_license_nixpkgs_does_not_know(mocker):
    nixpkgs_answering(mocker, {})

    assert LicenseLookup().attribute_for(NOT_IN_THE_HAND_WRITTEN_MAP) is None


def test_asks_nixpkgs_once_however_often_it_is_queried(mocker):
    check_output = nixpkgs_answering(mocker, {})
    lookup = LicenseLookup()

    lookup.attribute_for(NOT_IN_THE_HAND_WRITTEN_MAP)
    lookup.attribute_for(NOT_IN_THE_HAND_WRITTEN_MAP)

    check_output.assert_called_once()


def test_shares_what_nixpkgs_answered_with_no_other_lookup(mocker):
    check_output = nixpkgs_answering(mocker, {})

    LicenseLookup().attribute_for(NOT_IN_THE_HAND_WRITTEN_MAP)
    LicenseLookup().attribute_for(NOT_IN_THE_HAND_WRITTEN_MAP)

    assert check_output.call_count == 2


@pytest.mark.parametrize(
    "failure",
    [
        FileNotFoundError("nix-instantiate"),
        CalledProcessError(1, "nix-instantiate"),
    ],
)
def test_reports_a_lookup_nixpkgs_cannot_answer(mocker, failure):
    mocker.patch("pip2nix.license_lookup.check_output", side_effect=failure)

    with pytest.raises(ReportError):
        LicenseLookup().attribute_for(NOT_IN_THE_HAND_WRITTEN_MAP)


def nixpkgs_answering(mocker, known):
    return mocker.patch(
        "pip2nix.license_lookup.check_output",
        return_value=json.dumps(json.dumps(known)).encode("utf-8"),
    )


def nixpkgs_refusing_to_be_asked(mocker):
    return mocker.patch(
        "pip2nix.license_lookup.check_output",
        side_effect=AssertionError("Asked nixpkgs what it knows."),
    )
