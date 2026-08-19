Stop emitting ``checkInputs``. It was written as an empty list on
every package and filled on none, and an omitted argument takes
``buildPythonPackage``'s own default, so no build changes. Test
dependencies stay the customization layer's, where
``nativeCheckInputs`` is the attribute for them; see ADR-0011.
