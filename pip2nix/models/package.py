import os
from dataclasses import dataclass, field

from .. import nix_base32
from .source import Archive, LocalPath, Repository, Source


# The `buildPythonPackage` builders pip2nix generates.
WHEEL = "wheel"
SETUPTOOLS = "setuptools"
PYPROJECT = "pyproject"

# Written out rather than joined, so the source shows the shape it
# emits. Both are `str.format` templates, hence the doubled braces.
_PACKAGE_TEMPLATE = """\
super.buildPythonPackage rec {{
  {args}
}};"""

_META_TEMPLATE = """\
meta = {{
  {meta_args}
}};"""

# Rendered in this order; every other argument follows them sorted.
_LEADING_ARGUMENTS = ("pname", "version", "src", "format", "doCheck")


def indent(amount, string):
    lines = string.splitlines()
    if len(lines) == 0:
        return ""
    elif len(lines) == 1:
        return lines[0]
    else:
        return lines[0] + "\n" + "\n".join(" " * amount + line for line in lines[1:])


@dataclass(frozen=True)
class PythonPackage:
    """
    A package as the arguments ``buildPythonPackage`` takes, rather than
    as facts about a Python package.

    :param dependencies: list of (name, version) pairs.
    :param setup_requires: names of the packages needed to build it.
    :param licenses: license names as declared, most authoritative
        spelling first.
    :param format: the `buildPythonPackage` builder, decided by the
        adapter from what the source declares.
    """

    name: str
    version: str
    dependencies: list[tuple[str, str]]
    source: Source
    setup_requires: list[str] = field(default_factory=list)
    licenses: list[str] = field(default_factory=list)
    format: str = SETUPTOOLS

    def to_nix(self, rendering):
        return _PACKAGE_TEMPLATE.format(args=indent(2, self._arguments(rendering)))

    def _arguments(self, rendering):
        arguments = self._build_arguments(rendering)
        trailing = sorted(set(arguments) - set(_LEADING_ARGUMENTS))
        rendered = [
            f"{name} = {arguments[name]};" for name in (*_LEADING_ARGUMENTS, *trailing)
        ]

        meta = self._meta(rendering)
        if meta:
            rendered.append(meta)

        return "\n".join(rendered)

    def _build_arguments(self, rendering):
        return dict(
            pname=f'"{self.name}"',
            version=f'"{self.version}"',
            format=f'"{self.format}"',
            doCheck="false",
            src=source_to_nix(self.source, rendering),
            buildInputs=_nix_list([]),
            nativeBuildInputs=_nix_list(self._native_build_inputs()),
            propagatedBuildInputs=_nix_list(self._propagated_build_inputs()),
        )

    def _propagated_build_inputs(self):
        return [f'self."{name}"' for name, _version in self.dependencies]

    def _native_build_inputs(self):
        unzip = ['pkgs."unzip"'] if self.source.url.endswith("zip") else []
        return unzip + [f'self."{name}"' for name in self.setup_requires]

    def _meta(self, rendering):
        arguments = self._meta_args(rendering)
        if not arguments:
            return ""
        rendered = "".join(
            f"{name} = {value};\n" for name, value in sorted(arguments.items())
        )
        return _META_TEMPLATE.format(meta_args=indent(2, rendered))

    def _meta_args(self, rendering):
        if not rendering.include_licenses:
            return {}
        license_nix = rendering.nix_licenses.to_nix(self.licenses, self.name)
        return {"license": license_nix} if license_nix else {}


def _nix_list(entries):
    if not entries:
        return "[]"
    return "[\n  " + "\n  ".join(entries) + "\n]"


def source_to_nix(source, rendering):
    match source:
        case Repository():
            return _fetchgit_to_nix(source, rendering)
        case LocalPath():
            return "./" + os.path.relpath(source.path)
        case Archive():
            return _fetchurl_to_nix(source)


def _fetchgit_to_nix(source, rendering):
    checkout = rendering.sources.repository(source)
    return "\n".join(
        (
            "fetchgit {{",
            '  url = "{url}";',
            '  rev = "{revision}";',
            '  sha256 = "{hash}";',
            "}}",
        )
    ).format(
        url=source.url,
        revision=checkout.rev,
        hash=checkout.sha256,
    )


def _fetchurl_to_nix(source):
    return "\n".join(
        ("fetchurl {{", '  url = "{url}";', '  sha256 = "{hash}";', "}}")
    ).format(
        url=source.url,
        hash=nix_base32.from_hex(source.sha256),
    )
