"""
Rendering what a package declares as the `meta.license` nixpkgs takes.
"""

import logging

from ..licenses import license_expression_members, nix_license_attribute


logger = logging.getLogger(__name__)


def license_to_nix(licenses, package_name):
    """
    The `meta.license` value, or None when nothing is declared.

    Only the spellings nixpkgs knows are rendered, an SPDX expression as
    every attribute it names. When nixpkgs knows none of them the most
    authoritative spelling is kept as a full name, which is the shape
    `nixpkgs.lib.licenses` entries have anyway.
    """
    attributes = []
    for license_name in licenses:
        for attribute in _attributes_of(license_name):
            if attribute not in attributes:
                attributes.append(attribute)

    if attributes:
        rendered = [_attribute_to_nix(attribute) for attribute in attributes]
    elif licenses:
        _warn_kept_as_full_name(licenses[0], package_name)
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
    attributes = [nix_license_attribute(member) for member in _members_of(declared)]
    return attributes if all(attributes) else []


def _members_of(declared):
    """
    The licenses a declared string names: itself, unless it is an
    expression naming several.
    """
    if nix_license_attribute(declared):
        return [declared]
    return license_expression_members(declared) or [declared]


def _warn_kept_as_full_name(declared, package_name):
    unresolved = [
        member for member in _members_of(declared) if not nix_license_attribute(member)
    ]
    logger.warning(
        'Keeping the license of "%s" as a full name: nixpkgs has no attribute for %s.',
        package_name,
        ", ".join(unresolved),
    )


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
