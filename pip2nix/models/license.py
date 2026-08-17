"""
Rendering what a package declares as the `meta.license` nixpkgs takes.
"""

from ..licenses import license_expression_members, nix_license_attribute


def license_to_nix(licenses):
    """
    The `meta.license` value, or None when nothing is declared.

    Only the spellings nixpkgs knows are rendered. When it knows none of
    them the most authoritative one is kept as a full name, which is the
    shape `nixpkgs.lib.licenses` entries have anyway.
    """
    attributes = []
    for license_name in licenses:
        for attribute in _attributes_of(license_name):
            if attribute not in attributes:
                attributes.append(attribute)

    if attributes:
        rendered = [_attribute_to_nix(attribute) for attribute in attributes]
    elif licenses:
        rendered = [_full_name_to_nix(licenses[0])]
    else:
        return None

    return "[ {licenses} ]".format(licenses=" ".join(rendered))


def _attributes_of(declared):
    """
    Every attribute a declared license resolves to, or none at all.

    An SPDX expression names distinct licenses, so one nixpkgs does not
    know makes the whole expression unusable: rendering the rest would
    state something narrower than the package declares.
    """
    attribute = nix_license_attribute(declared)
    if attribute:
        return [attribute]

    members = license_expression_members(declared)
    if not members:
        return []

    attributes = [nix_license_attribute(member) for member in members]
    return attributes if all(attributes) else []


def _attribute_to_nix(attribute):
    return f"pkgs.lib.licenses.{attribute}"


def _full_name_to_nix(license_name):
    return f'{{ fullName = "{_escape_nix_string(license_name)}"; }}'


def _escape_nix_string(value):
    """
    A string the index declared, made safe to place inside a Nix literal.

    Nothing upstream of this constrains what a package declares, and an
    unescaped quote ends the attribute while `${` starts an
    interpolation.
    """
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return escaped.replace("${", "\\${")
