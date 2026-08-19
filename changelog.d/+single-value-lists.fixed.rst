Accept a single value wherever a list is expected. ``constraints``,
``excluded_packages`` and ``extra_index_url`` refused
``constraints = constraints.txt`` and wanted a trailing comma,
reporting its absence as a type error that said nothing about commas.
``requirements`` always accepted it.
