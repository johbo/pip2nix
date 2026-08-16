import json

from pip2nix import licenses


def raise_on_call(*args, **kwargs):
    raise Exception("Must not be called")


def test_loads_data_once(monkeypatch):
    stub_data = {"stub": {"attr": "value"}}
    stub_value = json.dumps(json.dumps(stub_data)).encode("utf-8")
    licenses._nix_licenses = None

    monkeypatch.setattr(licenses, "check_output", lambda *args: stub_value)
    licenses.get_nix_licenses()
    monkeypatch.setattr(licenses, "check_output", raise_on_call)
    licenses.get_nix_licenses()

    assert licenses._nix_licenses == stub_data
