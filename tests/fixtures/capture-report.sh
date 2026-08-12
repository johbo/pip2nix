#!/usr/bin/env bash
#
# Capture an installation report as a test fixture.
#
# The fixtures are real pip output, trimmed to the fields pip2nix reads
# so that a diff stays readable. Re-run this to refresh one against a
# newer pip:
#
#   ./capture-report.sh report-git.json \
#       'six @ git+https://github.com/benjaminp/six@1.16.0'
#
# Nothing is pinned on purpose: the capture uses whichever pip nixpkgs
# currently provides, which is what makes re-running it worthwhile.
# Needs network, and the resolution has to be reproducible -- pin every
# requirement to an exact version or commit, or the refreshed fixture
# will not match what the tests assert.
set -euo pipefail

if [ "$#" -lt 2 ]; then
    echo "usage: $0 <fixture.json> <requirement>..." >&2
    exit 2
fi

fixture="$1"
shift

fixtures_dir="$(dirname "$(readlink -f "$0")")"
raw="$(mktemp --tmpdir --directory pip2nix-capture-XXXXXX)/report.json"

nix shell nixpkgs#python3Packages.pip --command \
    pip install --dry-run --ignore-installed --quiet --report "$raw" "$@"

# Keeps what pip2nix reads: the source, the direct/transitive flag, the
# extras a top level entry asked for, and the metadata edges are
# attributed from. The prose fields are what make an untrimmed report
# unreadable in review.
nix shell nixpkgs#jq --command jq --sort-keys '
    {
        version,
        pip_version,
        install: [.install[] | {
            download_info,
            requested,
            requested_extras,
            metadata: (.metadata | {
                metadata_version, name, version,
                requires_python, requires_dist, provides_extra
            })
        }],
        environment
    } | del(.. | nulls)
' "$raw" > "$fixtures_dir/$fixture"

echo "Wrote $fixtures_dir/$fixture" >&2
