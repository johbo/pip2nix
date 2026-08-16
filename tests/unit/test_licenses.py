import json

from pip2nix import licenses


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
