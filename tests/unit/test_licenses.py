import json
from subprocess import CalledProcessError

import pytest

from pip2nix import licenses
from pip2nix.errors import ReportError


def test_maps_a_license_the_hand_written_map_knows(mocker):
    mocker.patch("pip2nix.licenses._nix_licenses", {})

    assert licenses.nix_license_attribute("GPLv3") == "gpl3"


def test_maps_a_license_by_its_spdx_identifier(mocker):
    mocker.patch(
        "pip2nix.licenses._nix_licenses",
        {"gpl3Plus": {"spdxId": "gpl-3.0-or-later"}},
    )

    assert licenses.nix_license_attribute("GPL-3.0-or-later") == "gpl3Plus"


def test_maps_nothing_for_a_license_nixpkgs_does_not_know(mocker):
    mocker.patch("pip2nix.licenses._nix_licenses", {})

    assert licenses.nix_license_attribute("Frobnicate 1.0") is None


def test_names_the_licenses_an_expression_carries():
    assert licenses.license_expression_members("Apache-2.0 OR BSD-2-Clause") == [
        "Apache-2.0",
        "BSD-2-Clause",
    ]


def test_names_the_licenses_of_an_expression_in_canonical_spelling():
    assert licenses.license_expression_members("apache-2.0 and mit") == [
        "Apache-2.0",
        "MIT",
    ]


def test_names_the_one_license_a_bare_identifier_carries():
    assert licenses.license_expression_members("MIT") == ["MIT"]


@pytest.mark.parametrize(
    "expression",
    [
        "GPL-2.0-or-later WITH Bison-exception-2.2",
        "(MIT OR Apache-2.0) AND BSD-3-Clause",
    ],
)
def test_names_nothing_for_an_expression_with_no_list_form(expression):
    assert licenses.license_expression_members(expression) is None


def test_names_nothing_for_what_is_not_an_expression():
    assert licenses.license_expression_members("Frobnicate 1.0") is None


def test_loads_data_once(mocker):
    stub_data = {"stub": {"attr": "value"}}
    mocker.patch("pip2nix.licenses._nix_licenses", None)
    check_output = mocker.patch(
        "pip2nix.licenses.check_output",
        return_value=json.dumps(json.dumps(stub_data)).encode("utf-8"),
    )

    licenses.get_nix_licenses()
    licenses.get_nix_licenses()

    assert licenses._nix_licenses == stub_data
    check_output.assert_called_once()


@pytest.mark.parametrize(
    "failure",
    [
        FileNotFoundError("nix-instantiate"),
        CalledProcessError(1, "nix-instantiate"),
    ],
)
def test_reports_a_lookup_nixpkgs_cannot_answer(mocker, failure):
    mocker.patch("pip2nix.licenses._nix_licenses", None)
    mocker.patch("pip2nix.licenses.check_output", side_effect=failure)

    with pytest.raises(ReportError):
        licenses.get_nix_licenses()
