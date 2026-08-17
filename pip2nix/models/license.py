"""
Rendering what a package declares as the `meta.license` nixpkgs takes.
"""

from ..licenses import nix_license_attribute


def license_to_nix(licenses):
    """
    The `meta.license` value, or None when nothing is declared.

    Only the spellings nixpkgs knows are rendered. When it knows none of
    them the most authoritative one is kept as a full name, which is the
    shape `nixpkgs.lib.licenses` entries have anyway.
    """
    attributes = []
    for license_name in licenses:
        attribute = nix_license_attribute(license_name)
        if attribute and attribute not in attributes:
            attributes.append(attribute)

    if attributes:
        rendered = [_attribute_to_nix(attribute) for attribute in attributes]
    elif licenses:
        rendered = [_full_name_to_nix(licenses[0])]
    else:
        return None

    return "[ {licenses} ]".format(licenses=" ".join(rendered))


def _attribute_to_nix(attribute):
    return f"pkgs.lib.licenses.{attribute}"


def _full_name_to_nix(license_name):
    return f'{{ fullName = "{license_name}"; }}'
