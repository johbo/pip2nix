import logging
import os

from .. import nix_base32
from ..errors import UnresolvableRevision


logger = logging.getLogger(__name__)

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


class PythonPackage:
    def __init__(
        self,
        name,
        version,
        dependencies,
        source,
        setup_requires=None,
        licenses=None,
        format=SETUPTOOLS,
    ):
        """
        :param dependencies: list of (name, version) pairs.
        :param setup_requires: names of the packages needed to build it.
        :param licenses: license names as declared, most authoritative
            spelling first.
        :param format: the `buildPythonPackage` builder, decided by the
            adapter from what the source declares.
        """
        self.name = name
        self.version = version
        self.dependencies = dependencies
        self.source = source
        self.check = False
        self.setup_requires = setup_requires or []
        self.licenses = licenses or []
        self.format = format

    def to_nix(self, rendering):
        return _PACKAGE_TEMPLATE.format(args=indent(2, self._arguments(rendering)))

    def _arguments(self, rendering):
        arguments = self._build_arguments(rendering)
        rendered = [f"{name} = {arguments.pop(name)};" for name in _LEADING_ARGUMENTS]
        rendered += [f"{name} = {value};" for name, value in sorted(arguments.items())]

        meta = self._meta(rendering)
        if meta:
            rendered.append(meta)

        return "\n".join(rendered)

    def _build_arguments(self, rendering):
        return dict(
            pname=f'"{self.name}"',
            version=f'"{self.version}"',
            format=f'"{self.format}"',
            doCheck="true" if self.check else "false",
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
    if source.vcs == "git":
        return _fetchgit_to_nix(source, rendering)
    elif source.vcs:
        raise NotImplementedError(
            f"Cannot render a {source.vcs} repository, pip2nix renders git."
        )
    elif source.scheme == "file":
        return "./" + os.path.relpath(source.path)
    elif source.scheme in ("http", "https"):
        return _fetchurl_to_nix(source, rendering)
    else:
        raise NotImplementedError(f'Unknown source scheme "{source.scheme}"')


def _fetchgit_to_nix(source, rendering):
    if not source.rev:
        raise UnresolvableRevision(
            f"No revision given for {source.url}. Refusing to generate a source "
            "which follows whatever the default branch points at."
        )
    hash, revision, _checkout = rendering.prefetch_git(source.url, source.rev)
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
        revision=revision,
        hash=hash,
    )


def _fetchurl_to_nix(source, rendering):
    if source.sha256:
        hash = nix_base32.from_hex(source.sha256)
    elif source.url in rendering.hashes:
        hash = rendering.hashes[source.url]
    else:
        logger.info("Prefetching %s.", source.url)
        hash = rendering.prefetch_url(source.url)
    return "\n".join(
        ("fetchurl {{", '  url = "{url}";', '  sha256 = "{hash}";', "}}")
    ).format(
        url=source.url,
        hash=hash,
    )
