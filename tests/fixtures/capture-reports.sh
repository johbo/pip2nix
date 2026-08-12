#!/usr/bin/env bash
#
# Re-generate every captured report fixture, so that each one has its
# requirement written down rather than remembered.
#
# `report-single-wheel.json` is deliberately absent: it is written by
# hand around an `.example` index url rather than captured.
#
# Refreshing against a newer pip can move the versions it resolves, so
# expect to update what the tests assert along with the fixtures.
set -euo pipefail

here="$(dirname "$(readlink -f "$0")")"

"$here/capture-report.sh" report-git.json \
    'six @ git+https://github.com/benjaminp/six@1.16.0'

"$here/capture-report.sh" report-trytond-account.json \
    'trytond_account == 7.0.28'
