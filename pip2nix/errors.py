"""
The failures a generation run raises across its own layers.
"""


class ReportError(Exception):
    pass


class UnresolvableRevision(Exception):
    pass
