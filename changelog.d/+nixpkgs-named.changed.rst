Name the nixpkgs a license query is answered by, and give up on one
that does not resolve. ``--licenses`` evaluates ``<nixpkgs>``, which
resolves from ``NIX_PATH``, so which nixpkgs answered depended on the
environment the command ran in without the run saying which it was. The
store path is now reported before the query, and a ``<nixpkgs>`` that
does not resolve fails after 30 seconds instead of blocking on a fetch
from the flake registry; see ADR-0015.
