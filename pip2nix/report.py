"""
Translation of pip's installation report into packages and sources.

The report is the documented, versioned JSON description of what pip would
install. Reading it is all this module does: the run that produced it belongs
to `resolver.py`, and nothing here knows how pip is invoked.
"""

from dataclasses import replace

from packaging.utils import canonicalize_name

from .build_system import read_build_system
from .dependencies import resolve_dependencies
from .errors import ReportError
from .models.package import PYPROJECT, SETUPTOOLS, WHEEL, PythonPackage
from .models.source import Source
from .prefetch import prefetch_url_path


REPORT_VERSION = "1"

REMOTE_SCHEMES = ("http", "https")

LICENSE_CLASSIFIER = "License ::"


def resolve_packages(resolver, git_sources, only_direct=False, excluded=()):
    resolver.check_version()
    report = resolver.resolve()
    packages = packages_from_report(report, only_direct=only_direct, excluded=excluded)
    packages = resolve_source_distributions(packages, resolver)
    return read_build_systems(packages, report["environment"], git_sources)


def packages_from_report(report, only_direct=False, excluded=()):
    entries = _without_excluded(_entries_of(report), excluded)
    dependencies = resolve_dependencies(entries, report["environment"])
    if only_direct:
        entries = [entry for entry in entries if entry["requested"]]
    return [_package_from_entry(entry, dependencies) for entry in entries]


def resolve_source_distributions(packages, resolver):
    for package in packages:
        if needs_source_distribution(package.source):
            report = resolver.resolve_source(package)
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


def read_build_systems(packages, environment, git_sources):
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
        path = _local_path(package.source, git_sources)
        build_system = read_build_system(path, environment)
        package.setup_requires = build_system.requires
        package.format = PYPROJECT if build_system.declared else SETUPTOOLS
    return packages


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


def _local_path(source, git_sources):
    """
    Where the source can be read.

    It is fetched to get there, which for a repository is the clone the
    renderer needs anyway and for an archive is a store path nix keeps.
    """
    if source.vcs == "git":
        return git_sources.fetch(source).path
    if source.scheme == "file":
        return source.path
    return prefetch_url_path(source.url, source.sha256)


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
