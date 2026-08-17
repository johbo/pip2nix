"""
Putting a source into the Nix store, through the `nix-prefetch-*` tools.

Everything that reaches the network or the store on a generation run lives
here, so that neither the renderer nor the report adapter has to carry a
subprocess of its own.
"""

import json
import re
from functools import cache
from subprocess import check_output

COMMIT_ID_RE = re.compile("^[a-fA-F0-9]{40}$")


class UnresolvableRevision(Exception):
    pass


@cache
def prefetch_git(url, rev):
    """
    Clone `url` at `rev` into the store, as `(hash, revision, path)`.

    Memoized because a revision is immutable content, and both the
    checkout -- which is where the build system is declared -- and the
    hash are wanted for the same source.
    """
    print(f"Prefetching {url} at revision {rev}.")
    out = check_output(
        ["nix-prefetch-git", "--url", url, "--rev", resolve_git_revision(url, rev)]
    )
    data = json.loads(out.decode("utf-8"))
    return data["sha256"], data["rev"], data["path"]


def prefetch_url_path(url, sha256):
    """
    Download `url` into the store and return where it landed.

    The hash the index published is what keeps this cheap: nix has the
    file after the first generation and does not fetch it again.
    """
    print(f"Prefetching {url}.")
    out = check_output(
        ["nix-prefetch-url", "--print-path", "--type", "sha256", url, sha256]
    )
    return out.decode("utf-8").splitlines()[-1]


def prefetch_url(url):
    out = check_output(["nix-prefetch-url", url])
    data = out.decode("utf-8").strip()
    return data


def resolve_git_revision(url, rev):
    """
    Resolve `rev` against `url` the way pip resolves an `@rev` fragment.

    Resolving here rather than leaving it to `nix-prefetch-git` matters because
    that reads a bare name as a tag only, so pip and the prefetch would
    disagree about which commit a branch name means.
    """
    if COMMIT_ID_RE.match(rev):
        return rev

    refs = _list_remote_refs(url, rev)
    for candidate in ("refs/heads/" + rev, "refs/tags/" + rev, rev):
        if candidate in refs:
            return refs[candidate]

    raise UnresolvableRevision(f'Cannot resolve "{rev}" to a commit in {url}.')


def _list_remote_refs(url, pattern):
    out = check_output(["git", "ls-remote", "--", url, pattern])
    lines = out.decode("utf-8").splitlines()
    return {ref: sha for sha, ref in (line.split("\t") for line in lines)}
