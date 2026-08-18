"""
Putting a source into the Nix store, through the `nix-prefetch-*` tools.

Everything that reaches the store on a generation run lives here, so that
neither the renderer nor the report adapter has to carry a subprocess of
its own.
"""

import json
import re
from subprocess import CalledProcessError, check_output

from .errors import ReportError, UnresolvableRevision


COMMIT_ID_RE = re.compile("^[a-fA-F0-9]{40}$")


def prefetch_git(url, rev, expected_hash=None):
    resolved = resolve_git_revision(url, rev)
    argv = ["nix-prefetch-git", url, resolved]
    if expected_hash:
        argv.append(expected_hash)
    else:
        print(f"Prefetching {url} at revision {rev}.")
    out = _tool_output(argv, f"Cannot fetch {url} at revision {rev}")
    data = json.loads(out.decode("utf-8"))
    return data["sha256"], data["rev"] or resolved, data["path"]


def prefetch_url_path(url, sha256):
    """
    Download `url` into the store and return where it landed.

    The hash the index published is what keeps this cheap: nix has the
    file after the first generation and does not fetch it again.
    """
    print(f"Prefetching {url}.")
    out = _tool_output(
        ["nix-prefetch-url", "--print-path", "--type", "sha256", url, sha256],
        f"Cannot fetch {url}",
    )
    return out.decode("utf-8").splitlines()[-1]


def prefetch_url(url):
    out = _tool_output(["nix-prefetch-url", url], f"Cannot fetch {url}")
    return out.decode("utf-8").strip()


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
    out = _tool_output(
        ["git", "ls-remote", "--", url, pattern], f"Cannot list the refs of {url}"
    )
    lines = out.decode("utf-8").splitlines()
    return {ref: sha for sha, ref in (line.split("\t") for line in lines)}


def _tool_output(argv, failure):
    """
    What a tool wrote, or a reported failure when it could not run.

    The tools are external to pip2nix, so a missing one and a refused
    fetch are both things a user can act on rather than defects.
    """
    try:
        return check_output(argv)
    except (OSError, CalledProcessError) as error:
        raise ReportError(f"{failure}: {error}.")
