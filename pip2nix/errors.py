"""
The failure a generation run reports to its user.

It sits in a module of its own rather than in `report.py` so that
`dependencies.py` may raise it too: that module is below the adapter and
imports nothing from it.
"""


class ReportError(Exception):
    pass
