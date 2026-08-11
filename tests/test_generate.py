import pytest

pytest.skip(
    "generate.py imports pip internals removed after pip 20.x; "
    "the report-based generator replaces it, see ADR-0001",
    allow_module_level=True,
)

from unittest import mock

from pip2nix.generate import _is_direct_requirement


def test_is_direct_requirement_without_comes_from_considered_direct():
    stub_requirement = mock.Mock()
    stub_requirement.is_direct = True
    stub_requirement.comes_from = None

    assert _is_direct_requirement(stub_requirement)


def test_is_direct_requirement_from_constraints_not_considered_direct():
    stub_requirement = mock.Mock()
    stub_requirement.is_direct = True
    stub_requirement.comes_from = "-c module-constraints.txt"

    assert not _is_direct_requirement(stub_requirement)
