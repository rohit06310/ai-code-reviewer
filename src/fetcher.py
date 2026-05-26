"""
fetcher.py
----------
Responsible for retrieving the pull-request diff from the GitHub REST API.

Single responsibility: talk to GitHub, return the raw unified diff as a string.
No parsing, no AI calls, no business logic.
"""

import sys
import urllib.request
import urllib.error

from src import config


def fetch_diff() -> str:
    """
    Fetch the unified diff for the configured pull request from GitHub.

    Uses:
        config.GITHUB_TOKEN       — Bearer token for authentication.
        config.GITHUB_REPOSITORY  — "owner/repo" repository slug.
        config.PR_NUMBER          — Pull-request number (string).

    Returns:
        str: Raw unified diff text, or an empty string if the PR has no diff.

    Raises:
        SystemExit(1): If the GitHub API returns a non-200 HTTP status.
    """
    # Build the API URL for the pull-request diff.
    url = (
        f"https://api.github.com/repos/{config.GITHUB_REPOSITORY}"
        f"/pulls/{config.PR_NUMBER}"
    )

    print(f"[fetcher] Fetching diff for PR #{config.PR_NUMBER} "
          f"in '{config.GITHUB_REPOSITORY}' ...")
    print(f"[fetcher] GET {url}")

    # -----------------------------------------------------------------
    # Build the HTTP request.
    # -----------------------------------------------------------------
    request = urllib.request.Request(url)

    # Request the diff media type instead of the default JSON payload.
    request.add_header("Accept", "application/vnd.github.v3.diff")

    # Authenticate with the GitHub token (required for private repos and
    # to avoid strict anonymous rate limits).
    request.add_header("Authorization", f"Bearer {config.GITHUB_TOKEN}")

    # GitHub recommends sending a descriptive User-Agent.
    request.add_header("User-Agent", "ai-code-reviewer/1.0")

    # -----------------------------------------------------------------
    # Execute the request.
    # -----------------------------------------------------------------
    try:
        with urllib.request.urlopen(request) as response:
            status_code: int = response.status

            if status_code != 200:
                # Shouldn't normally reach here (non-2xx raises HTTPError),
                # but guard defensively.
                print(
                    f"[fetcher] ERROR: GitHub API returned status {status_code}. "
                    "Check GITHUB_TOKEN, GITHUB_REPOSITORY, and PR_NUMBER."
                )
                sys.exit(1)

            raw_bytes: bytes = response.read()

    except urllib.error.HTTPError as exc:
        # HTTPError is raised for 4xx / 5xx responses.
        print(
            f"[fetcher] ERROR: GitHub API responded with HTTP {exc.code} "
            f"({exc.reason}). "
            "Verify that GITHUB_TOKEN is valid and has 'repo' scope, "
            "that GITHUB_REPOSITORY and PR_NUMBER are correct."
        )
        sys.exit(1)

    except urllib.error.URLError as exc:
        # URLError covers network-level failures (DNS, timeout, etc.).
        print(f"[fetcher] ERROR: Failed to reach GitHub API — {exc.reason}")
        sys.exit(1)

    # -----------------------------------------------------------------
    # Decode and validate the diff payload.
    # -----------------------------------------------------------------
    diff: str = raw_bytes.decode("utf-8", errors="replace")

    if not diff.strip():
        print(
            f"[fetcher] WARNING: PR #{config.PR_NUMBER} returned an empty diff. "
            "The PR may have no file changes."
        )
        return ""

    char_count: int = len(diff)
    print(f"[fetcher] Success — received {char_count:,} characters of diff.")

    return diff
