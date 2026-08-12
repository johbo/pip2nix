"""
Dependency edges, rebuilt from what each package declares.

pip's installation report carries `metadata.requires_dist`, which is
what a package declares rather than the edges the resolver chose.
Attributing them means evaluating PEP 508 markers against the
environment pip resolved for and keeping only the names the resolution
actually contains.
"""

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def resolve_dependencies(entries, environment):
    """
    Map each entry's name to the packages it depends on.

    Names are canonical throughout, and the values are the
    `(name, version)` pairs `PythonPackage` renders.
    """
    packages = {canonicalize_name(entry['metadata']['name']): entry
                for entry in entries}
    return {
        name: _dependencies_of(entry, packages, environment)
        for name, entry in packages.items()
    }


def _dependencies_of(entry, packages, environment):
    names = {canonicalize_name(requirement.name)
             for requirement in _active_requirements(entry, environment)}
    return sorted((name, packages[name]['metadata']['version'])
                  for name in names if name in packages)


def _active_requirements(entry, environment):
    for declared in entry['metadata'].get('requires_dist') or []:
        requirement = Requirement(declared)
        if requirement.marker is None or requirement.marker.evaluate(
                environment):
            yield requirement
