"""
Resolution through pip's installation report.

pip is run as a subprocess and asked for a `--report`, the documented and
versioned JSON description of what it would install. Nothing on this path
touches `pip._internal`, which is the point of ADR-0001.
"""

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, replace

from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

from .build_system import read_build_system
from .config import Config
from .dependencies import resolve_dependencies
from .errors import ReportError
from .models.package import PYPROJECT, SETUPTOOLS, WHEEL, PythonPackage
from .models.source import Source
from .prefetch import prefetch_git, prefetch_url_path


REPORT_VERSION = "1"

MINIMUM_PIP_VERSION = "22.2"

REMOTE_SCHEMES = ("http", "https")

LICENSE_CLASSIFIER = "License ::"


def resolve_packages(config, python_executable):
    check_pip_version(python_executable)
    resolver = Resolver(python_executable, config)
    report = _read_report(resolver.argv())
    packages = packages_from_report(
        report,
        only_direct=config.get_config("pip2nix", "only_direct"),
        excluded=config.get_config("pip2nix", "excluded_packages"),
    )
    packages = resolve_source_distributions(packages, resolver)
    return read_build_systems(packages, report["environment"])


def packages_from_report(report, only_direct=False, excluded=()):
    entries = _without_excluded(_entries_of(report), excluded)
    dependencies = resolve_dependencies(entries, report["environment"])
    if only_direct:
        entries = [entry for entry in entries if entry["requested"]]
    return [_package_from_entry(entry, dependencies) for entry in entries]


def resolve_source_distributions(packages, resolver):
    for package in packages:
        if needs_source_distribution(package.source):
            report = _read_report(resolver.source_argv(package))
            package.source = source_distribution_of(package, report)
    return packages


def needs_source_distribution(source):
    """
    Whether Nix can build from the file pip resolved to.

    A wheel built for a platform links against libraries at paths that do not
    exist in the store, so ADR-0003 replaces it with the project's sdist. A
    `-any` wheel carries the same modules its sdist does and is left alone.
    """
    return source.path.endswith(".egg") or (
        _is_wheel(source) and not source.path.endswith("-any.whl")
    )


def _is_wheel(source):
    return source.path.endswith(".whl")


def source_distribution_of(package, report):
    entries = {_name_of(entry): entry for entry in _entries_of(report)}
    try:
        entry = entries[package.name]
    except KeyError:
        raise ReportError(
            f'Resolving "{package.name}" from its source distribution did not produce '
            "it at all."
        )
    if entry["metadata"]["version"] != package.version:
        raise ReportError(
            'Resolving "{name}" from its source distribution produced '
            "version {sdist} where the wheel resolved to {wheel}. Refusing "
            "to pin a source the rendered metadata does not describe.".format(
                name=package.name,
                sdist=entry["metadata"]["version"],
                wheel=package.version,
            )
        )
    return _source_from_download_info(entry["download_info"])


def read_build_systems(packages, environment):
    """
    Give every package the builder it declares and the backend it needs.

    The report carries core metadata, which has no build-system field, so the
    source itself is the only place this can come from. Deciding it here rather
    than in the renderer is what keeps the renderer from having to read
    sources.
    """
    for package in packages:
        if _is_wheel(package.source):
            package.format = WHEEL
            continue
        build_system = read_build_system(_local_path(package.source), environment)
        package.setup_requires = build_system.requires
        package.format = PYPROJECT if build_system.declared else SETUPTOOLS
    return packages


def check_pip_version(python_executable):
    """
    Refuse a pip that cannot write an installation report.

    `--report` arrived in pip 22.2. An older one rejects the option as a usage
    error, which reads as if the requirements were the problem.
    """
    try:
        output = subprocess.check_output([python_executable, "-m", "pip", "--version"])
    except (OSError, subprocess.CalledProcessError) as error:
        raise ReportError(f'Cannot run pip through "{python_executable}": {error}')

    version = parse_pip_version(output.decode("utf-8"))
    if version < Version(MINIMUM_PIP_VERSION):
        raise ReportError(
            f"pip {version} cannot write an installation report, pip2nix "
            f"needs {MINIMUM_PIP_VERSION} or newer."
        )


def parse_pip_version(output):
    """
    The version out of what `pip --version` prints.

    That is one line, `pip 25.3 from /nix/store/... (python 3.13)`.
    """
    words = output.split()
    try:
        return Version(words[1])
    except (IndexError, InvalidVersion):
        raise ReportError(f'Cannot read a pip version from "{output.strip()}".')


@dataclass(frozen=True)
class Resolver:
    """
    How pip is invoked: an interpreter, and the configuration its argument
    vector is built from.

    The two travelled as a pair through every function that had to reach pip,
    which is what they are together rather than what either is alone.
    """

    python_executable: str
    config: Config

    def argv(self):
        argv = self._argv()

        for constraint in self.config.get_constraints():
            argv += ["--constraint", constraint]

        for kind, requirement in self.config.get_requirements():
            if kind == "-r":
                argv += ["--requirement", requirement]
            elif kind == "-e":
                raise ReportError(
                    f'Editable requirements are not supported: "{requirement}". '
                    "The report describes them as a local directory, which loses "
                    "the url and the revision they were installed from."
                )
            else:
                argv.append(requirement)

        return argv

    def source_argv(self, package):
        """
        Refuse a wheel to this package alone.

        pip hands its format control on to the build environments it
        creates, so a second name here is a backend it would compile
        rather than install. That is what ADR-0005 exists to avoid.
        """
        return self._argv() + [
            "--no-deps",
            "--no-binary",
            package.name,
            f"{package.name}=={package.version}",
        ]

    def _argv(self):
        argv = [
            self.python_executable,
            "-m",
            "pip",
            "install",
            "--dry-run",
            "--ignore-installed",
            "--quiet",
        ]

        indexes = self.config.get_indexes()
        if indexes:
            argv += ["--index-url", indexes[0]]
            for extra_index in indexes[1:]:
                argv += ["--extra-index-url", extra_index]
        else:
            argv.append("--no-index")

        return argv


def _entries_of(report):
    version = report.get("version")
    if version != REPORT_VERSION:
        raise ReportError(
            f'Cannot read an installation report of version "{version}", '
            f'pip2nix understands version "{REPORT_VERSION}".'
        )
    return report["install"]


def _without_excluded(entries, excluded):
    """
    Drop the packages a consumer does not want generated.

    Removing them before dependencies are attributed also removes the
    edges naming them, so an excluded package is absent from the file
    entirely. `only_direct` filters after attribution instead, so that
    a package it emits keeps propagating what it needs.
    """
    excluded_names = {canonicalize_name(name) for name in excluded}
    return [entry for entry in entries if _name_of(entry) not in excluded_names]


def _name_of(entry):
    return canonicalize_name(entry["metadata"]["name"])


def _local_path(source):
    """
    Where the source can be read.

    It is fetched to get there, which for a repository is the clone the
    renderer needs anyway and for an archive is a store path nix keeps.
    """
    if source.vcs == "git":
        _hash, _rev, checkout = prefetch_git(source.url, source.rev)
        return checkout
    if source.scheme == "file":
        return source.path
    return prefetch_url_path(source.url, source.sha256)


def _read_report(argv):
    with tempfile.TemporaryDirectory(prefix="pip2nix-") as directory:
        report_path = os.path.join(directory, "report.json")
        try:
            subprocess.check_call(argv + ["--report", report_path])
        except subprocess.CalledProcessError as error:
            raise ReportError(
                "pip could not resolve the requirements, it exited with "
                f"status {error.returncode}."
            )
        with open(report_path) as report_file:
            return json.load(report_file)


def _package_from_entry(entry, dependencies):
    metadata = entry["metadata"]
    name = _name_of(entry)
    return PythonPackage(
        name=name,
        version=metadata["version"],
        dependencies=dependencies[name],
        source=_source_from_download_info(entry["download_info"]),
        licenses=_licenses_from_metadata(metadata),
    )


def _licenses_from_metadata(metadata):
    """
    The licenses a package declares, most authoritative spelling first.

    PEP 639 replaced both the free text `License` field and the
    `License ::` classifiers with an SPDX expression, and a package can
    carry any combination of the three.
    """
    candidates = [
        metadata[field]
        for field in ("license_expression", "license")
        if metadata.get(field)
    ]
    candidates.extend(
        classifier.split("::")[-1].strip()
        for classifier in metadata.get("classifier", ())
        if classifier.startswith(LICENSE_CLASSIFIER)
    )
    # setuptools used to write the placeholder out as a license itself.
    return [candidate for candidate in candidates if candidate != "UNKNOWN"]


def _source_from_download_info(download_info):
    url = download_info["url"]
    if "vcs_info" in download_info:
        return _repository_source(url, download_info["vcs_info"])
    if download_info.get("dir_info", {}).get("editable"):
        raise ReportError(
            f'Cannot generate a source for "{url}": the report describes an '
            "editable requirement as the local directory it would be "
            "checked out into, which loses the url and the revision it "
            "comes from."
        )

    source = Source.from_url(url)
    if source.scheme in REMOTE_SCHEMES:
        return replace(source, sha256=_sha256_of(download_info))
    return source


def _repository_source(url, vcs_info):
    vcs = vcs_info["vcs"]
    if vcs != "git":
        raise ReportError(
            f'Cannot generate a source for "{url}": pip2nix renders git '
            f"repositories, this one is {vcs}."
        )
    return replace(Source.from_url(url), vcs=vcs, rev=vcs_info["commit_id"])


def _sha256_of(download_info):
    hashes = download_info.get("archive_info", {}).get("hashes", {})
    try:
        return hashes["sha256"]
    except KeyError:
        raise ReportError(
            'The index published no sha256 for "{}". Refusing to generate '
            "a source without a hash to pin it.".format(download_info["url"])
        )
