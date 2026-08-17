"""
The infrastructure this suite assumes, verified before any of it runs.
"""

import subprocess

import pytest


# Long enough that a registry which does answer is not cut off, short
# enough that one which does not costs a wait rather than an evening.
NIXPKGS_TIMEOUT_SECONDS = 30

DEVSHELL_HINT = (
    "`<nixpkgs>` does not resolve. Run the suite through `just "
    "test-integration`, which enters the devShell that sets NIX_PATH."
)


@pytest.fixture(scope="session", autouse=True)
def resolvable_nixpkgs():
    """
    `<nixpkgs>` answering from the search path rather than from a fetch.

    Three tests reach it -- the license lookup, the profile build and the
    scaffolded `default.nix` -- and none of them passes nix a timeout, so
    an unanswered `<nixpkgs>` is a wait of minutes at every call instead
    of one failure here.
    """
    try:
        subprocess.run(
            ["nix-instantiate", "--eval", "--expr", "<nixpkgs>"],
            capture_output=True,
            check=True,
            text=True,
            timeout=NIXPKGS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(
            f"{DEVSHELL_HINT} It did not answer within {NIXPKGS_TIMEOUT_SECONDS}s."
        )
    except subprocess.CalledProcessError as error:
        pytest.fail(f"{DEVSHELL_HINT} nix said: {error.stderr.strip()}")
