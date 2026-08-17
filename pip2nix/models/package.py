import os

from .. import nix_base32
from ..licenses import (
    license_attribute_to_nix,
    license_full_name_to_nix,
    nix_license_attribute,
)
from ..prefetch import UnresolvableRevision, prefetch_git, prefetch_url

# The `buildPythonPackage` builders pip2nix generates.
WHEEL = "wheel"
SETUPTOOLS = "setuptools"
PYPROJECT = "pyproject"


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

    def to_nix(self, include_lic, cache=None):
        template = "\n".join(
            (
                "super.buildPythonPackage rec {{",
                "  {args}",
                "}};",
            )
        )
        meta_template = "\n".join(
            (
                "meta = {{",
                "  {meta_args}",
                "}};",
            )
        )

        args = dict(
            pname=f'"{self.name}"',
            version=f'"{self.version}"',
            format=f'"{self.format}"',
            doCheck="true" if self.check else "false",
            src=source_to_nix(self.source, cache=cache),
            buildInputs="[]",
            checkInputs="[]",
            nativeBuildInputs="[]",
            propagatedBuildInputs="[]",
        )

        if self.dependencies:
            args.update(
                dict(
                    propagatedBuildInputs="[\n  "
                    + (
                        "\n  ".join(
                            f'self."{name}"' for name, version in self.dependencies
                        )
                    )
                    + "\n]"
                )
            )

        unzip = self.source.url.endswith("zip")
        if unzip or self.setup_requires:
            args.update(
                dict(
                    nativeBuildInputs="[\n  "
                    + (
                        unzip
                        and self.setup_requires
                        and 'pkgs."unzip"\n  '
                        or unzip
                        and 'pkgs."unzip"'
                        or ""
                    )
                    + (
                        "\n  ".join(
                            f'self."{name}"' for name in self.setup_requires or ()
                        )
                    )
                    + "\n]"
                )
            )

        # Prepare meta arguments.
        meta_args = dict()
        if include_lic:
            license_nix = self.get_license_nix()
            if license_nix:
                meta_args["license"] = license_nix

        # Render name first
        raw_args = "pname = {};\n".format(args.pop("pname"))
        raw_args += "version = {};\n".format(args.pop("version"))
        raw_args += "src = {};\n".format(args.pop("src"))
        raw_args += "format = {};\n".format(args.pop("format"))
        raw_args += "doCheck = {};".format(args.pop("doCheck"))
        for k, v in sorted(args.items()):
            raw_args += f"\n{k} = {v};"

        # Render meta arguments.
        if meta_args:
            raw_meta_args = ""
            for k, v in sorted(meta_args.items()):
                raw_meta_args += f"{k} = {v};\n"
            meta = meta_template.format(meta_args=indent(2, raw_meta_args))
            raw_args += f"\n{meta}"

        return template.format(args=indent(2, raw_args))

    def get_license_nix(self):
        """
        The `meta.license` value, or None when nothing is declared.

        Only the spellings nixpkgs knows are rendered. When it knows
        none of them the most authoritative one is kept as a full name,
        which is the shape `nixpkgs.lib.licenses` entries have anyway.
        """
        attributes = []
        for license_name in self.licenses:
            attribute = nix_license_attribute(license_name)
            if attribute and attribute not in attributes:
                attributes.append(attribute)

        if attributes:
            rendered = [license_attribute_to_nix(attribute) for attribute in attributes]
        elif self.licenses:
            rendered = [license_full_name_to_nix(self.licenses[0])]
        else:
            return None

        return "[ {licenses} ]".format(licenses=" ".join(rendered))


def source_to_nix(source, cache=None):
    if source.vcs == "git":
        return _fetchgit_to_nix(source)
    elif source.vcs:
        raise NotImplementedError(
            f"Cannot render a {source.vcs} repository, pip2nix renders git."
        )
    elif source.scheme == "file":
        return "./" + os.path.relpath(source.path)
    elif source.scheme in ("http", "https"):
        return _fetchurl_to_nix(source, cache or {})
    else:
        raise NotImplementedError(f'Unknown source scheme "{source.scheme}"')


def _fetchgit_to_nix(source):
    if not source.rev:
        raise UnresolvableRevision(
            f"No revision given for {source.url}. Refusing to generate a source "
            "which follows whatever the default branch points at."
        )
    hash, revision, _checkout = prefetch_git(source.url, source.rev)
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


def _fetchurl_to_nix(source, cache):
    if source.sha256:
        hash = nix_base32.from_hex(source.sha256)
    elif source.url in cache:
        hash = cache[source.url]
    else:
        print(f"Prefetching {source.url}.")
        hash = prefetch_url(source.url)
    return "\n".join(
        ("fetchurl {{", '  url = "{url}";', '  sha256 = "{hash}";', "}}")
    ).format(
        url=source.url,
        hash=hash,
    )
