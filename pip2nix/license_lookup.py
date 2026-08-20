"""
Mapping a declared license name onto a `nixpkgs.lib.licenses` attribute, which
means asking nixpkgs what it knows.
"""

import json
from contextlib import suppress
from subprocess import CalledProcessError, check_output

from .errors import ReportError


# Mapping from license name in setup.py to attribute in nixpkgs.lib.licenses.
# TODO: Think about providing this from outside, maybe from a file.
case_sensitive_license_nix_map = {
    "Apache 2.0": "asl20",
    "Apache License, Version 2.0": "asl20",
    "Apache Software License": "asl20",
    "BSD license": "bsdOriginal",
    "BSD": "bsdOriginal",
    "GNU GPLv2 or any later version": "gpl2Plus",
    "GNU General Public License v2 or later (GPLv2+)": "gpl2Plus",
    "GNU General Public License v3 or later (GPLv3+)": "gpl3Plus",
    "GNU Lesser General Public License v2 or later (LGPLv2+)": "lgpl2Plus",
    "GPLv2 or later": "gpl2Plus",
    "GPLv2": "gpl2",
    "GPLv3": "gpl3",
    "LGPLv2.1 or later": "lgpl21Plus",
    "PSF License": "psfl",
    "PSF": "psfl",
    "Python Software Foundation License": "psfl",
    "Python style": "psfl",
    "Two-clause BSD license": "bsd2",
    "ZPL 2.1": "zpl21",
    "ZPL": "zpl21",
    "Zope Public License": "zpl21",
}
license_nix_map = {
    name.lower(): nix_attr for name, nix_attr in case_sensitive_license_nix_map.items()
}


class LicenseLookup:
    def __init__(self):
        self._nix_licenses = None

    def attribute_for(self, license_name):
        """
        The `nixpkgs.lib.licenses` attribute a license name maps to, if any.

        The names a package declares are free text, an SPDX identifier or a
        trove classifier, so the lookup goes through the hand-written map
        first and then through every value nixpkgs records for a license --
        `spdxId` among them, which is what makes SPDX identifiers resolve.
        """
        license_name = license_name.lower()

        attribute = license_nix_map.get(license_name)
        if attribute:
            return attribute

        for attribute, nix_license_data in self._known_to_nixpkgs().items():
            if license_name in nix_license_data.values():
                return attribute

        return None

    def _known_to_nixpkgs(self):
        if self._nix_licenses is None:
            self._nix_licenses = _ask_nixpkgs()
        return self._nix_licenses


def _ask_nixpkgs():
    # `lib.licenses` carries the SPDX operators `AND`, `OR`, `PLUS`
    # and `WITH` next to the licenses themselves, and `toJSON`
    # refuses to serialize a function.
    try:
        nix_licenses_json = check_output(
            [
                "nix-instantiate",
                "--eval",
                "--expr",
                (
                    "with import <nixpkgs> { }; builtins.toJSON "
                    "(lib.filterAttrs (name: value: builtins.isAttrs value) "
                    "lib.licenses)"
                ),
            ]
        )
    except (OSError, CalledProcessError) as error:
        raise ReportError(
            f"Cannot ask nixpkgs which licenses it knows: {error}. "
            "`--licenses` needs a `<nixpkgs>` that resolves."
        )

    nix_licenses = json.loads(json.loads(nix_licenses_json.decode("utf-8")))

    for entry in nix_licenses.values():
        for key, value in entry.items():
            # A value without lower() is not a name to match against.
            with suppress(AttributeError):
                entry[key] = value.lower()

    return nix_licenses
