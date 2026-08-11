"""Characterisation tests for the `toml` library's pyproject.toml defects.

pip 20.1.1 -- the version the working generator is pinned to -- vendors
this library. Every 0.10.x release implements TOML 0.5 and fails on
constructs that TOML 1.0 permits, which is what breaks generation
against 2025-era package metadata. pip2nix itself no longer uses it:
`models/package.py` reads `pyproject.toml` with stdlib `tomllib`.

These tests assert the *broken* behaviour on purpose. If one starts
failing, the dependency has been fixed or replaced, and that is a result
worth noticing.
"""

import tomllib

import pytest
import toml

# MarkupSafe 3.x uses this shape in [tool.tox.env_run_base]. It is why
# nix-tryton has to pin MarkupSafe < 3 -- 2.1.x ships no pyproject.toml
# at all, so nothing gets parsed.
NESTED_ARRAY_WITH_INLINE_TABLE = """\
commands = [[
    "pytest",
    {replace = "posargs", default = [], extend = true},
]]
"""

HETEROGENEOUS_ARRAY = 'commands = ["pytest", {replace = "posargs"}]\n'


def test_nested_array_with_inline_table_is_valid_toml():
    parsed = tomllib.loads(NESTED_ARRAY_WITH_INLINE_TABLE)

    assert parsed["commands"] == [
        ["pytest", {"replace": "posargs", "default": [], "extend": True}]
    ]


def test_toml_raises_index_error_on_nested_array_with_inline_table():
    with pytest.raises(IndexError):
        toml.loads(NESTED_ARRAY_WITH_INLINE_TABLE)


def test_heterogeneous_array_is_valid_toml():
    parsed = tomllib.loads(HETEROGENEOUS_ARRAY)

    assert parsed["commands"] == ["pytest", {"replace": "posargs"}]


def test_toml_rejects_heterogeneous_array():
    with pytest.raises(toml.TomlDecodeError):
        toml.loads(HETEROGENEOUS_ARRAY)
