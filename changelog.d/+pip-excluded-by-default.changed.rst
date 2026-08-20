Exclude ``pip`` from the generated file by default, beside
``setuptools`` and ``wheel``. An attribute named ``pip`` shadows the one
nixpkgs bootstraps its Python package set with, so a requirement set
that resolves pip would otherwise generate a file that breaks the
overlay composing it.
