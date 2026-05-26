"""
commenter.py
------------
Responsible for formatting AI-detected code issues as Markdown and posting
them as pull-request comments via the GitHub REST API.

Single responsibility: take a list of issue dicts, post them to the GitHub PR.
No AI calls, no diff parsing, no business logic beyond formatting and HTTP.
"""

import json
import urllib.request
import urllib.error

from src import config


# ---------------------------------------------------------------------------
# Severity icon mapping
# ---------------------------------------------------------------------------

# Maps the severity string returned by the AI to a coloured emoji indicator.
# Used in comment headers so reviewers can triage issues at a glance.
SEVERITY_ICONS: dict[str, str] = {
    "error":      "🔴",
    "warning":    "🟡",
    "suggestion": "🔵",
}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _build_comment_body(issue: dict) -> str:
    """
    Format a single issue dict into a Markdown comment string.

    Expected *issue* keys (all str except line which may be int):
        file, line, severity, message, fix

    Args:
        issue: A single issue dictionary as returned by reviewer.review_chunk().

    Returns:
        str: Formatted Markdown ready to post as a GitHub PR comment.
    """
    file_path: str = issue.get("file", "unknown file")
    line:      int  = issue.get("line", 0)
    severity:  str  = issue.get("severity", "suggestion").lower()
    message:   str  = issue.get("message", "No message provided.")
    fix:       str  = issue.get("fix", "No fix suggested.")

    # Fall back to the suggestion icon for any unrecognised severity value.
    icon: str = SEVERITY_ICONS.get(severity, SEVERITY_ICONS["suggestion"])

    # Capitalise the severity label for display purposes.
    severity_label = severity.capitalize()

    body = (
        f"## {icon} {severity_label}: `{file_path}` — Line {line}\n\n"
        f"{message}\n\n"
        f"**Suggested fix:**\n"
        f"```python\n"
        f"{fix}\n"
        f"```\n\n"
        f"---\n"
        f"*Posted by AI Code Reviewer*"
    )

    return body


def _post_single_comment(body: str) -> bool:
    """
    Post a single Markdown comment to the configured GitHub pull request.

    GitHub treats PR comments as issue comments, so the endpoint is:
        POST /repos/{owner}/{repo}/issues/{pr_number}/comments

    Args:
        body: Markdown-formatted comment string.

    Returns:
        bool: True if the comment was created (HTTP 201), False otherwise.
    """
    url = (
        f"https://api.github.com/repos/{config.GITHUB_REPOSITORY}"
        f"/issues/{config.PR_NUMBER}/comments"
    )

    payload: bytes = json.dumps({"body": body}).encode("utf-8")

    request = urllib.request.Request(url, data=payload, method="POST")
    request.add_header("Accept",        "application/vnd.github.v3+json")
    request.add_header("Authorization", f"Bearer {config.GITHUB_TOKEN}")
    request.add_header("Content-Type",  "application/json")
    request.add_header("User-Agent",    "ai-code-reviewer/1.0")

    try:
        with urllib.request.urlopen(request) as response:
            return response.status == 201

    except urllib.error.HTTPError as exc:
        print(
            f"[commenter] ERROR: GitHub API returned HTTP {exc.code} "
            f"({exc.reason}) while posting comment."
        )
        return False

    except urllib.error.URLError as exc:
        print(f"[commenter] ERROR: Failed to reach GitHub API — {exc.reason}")
        return False


def _post_clean_comment() -> None:
    """
    Post a single 'all clear' comment when the AI found no issues.

    This gives reviewers positive confirmation that the automated review ran
    successfully, rather than leaving them to wonder if it was skipped.
    """
    body = (
        "## ✅ AI Code Review — No Issues Found\n\n"
        "The automated review completed successfully and detected **no issues** "
        "in this pull request.\n\n"
        "---\n"
        "*Posted by AI Code Reviewer*"
    )

    if _post_single_comment(body):
        print("[commenter] ✅ Clean-bill-of-health comment posted successfully.")
    else:
        print("[commenter] ❌ Failed to post clean-bill-of-health comment.")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def post_all_comments(issues: list[dict]) -> None:
    """
    Post every issue in *issues* as a separate GitHub PR comment.

    If *issues* is empty, a single 'no issues found' comment is posted instead
    so the PR always receives feedback confirming the review ran.

    Progress and success/failure are printed for each comment so CI logs
    remain informative without verbose debugging overhead.

    Args:
        issues: Combined list of issue dicts from reviewer.review_all_chunks().
    """
    if not issues:
        print("[commenter] No issues found — posting clean review comment.")
        _post_clean_comment()
        return

    total   = len(issues)
    success = 0

    print(f"[commenter] Posting {total} comment(s) to PR #{config.PR_NUMBER} ...")

    for index, issue in enumerate(issues, start=1):
        file_path = issue.get("file", "unknown")
        line      = issue.get("line", "?")
        severity  = issue.get("severity", "?")
        icon      = SEVERITY_ICONS.get(severity, "🔵")

        body = _build_comment_body(issue)
        posted = _post_single_comment(body)

        if posted:
            success += 1
            print(
                f"[commenter] ✅ {index}/{total} posted — "
                f"{icon} {severity} in {file_path}:{line}"
            )
        else:
            print(
                f"[commenter] ❌ {index}/{total} failed  — "
                f"{icon} {severity} in {file_path}:{line}"
            )

    print(
        f"[commenter] Summary: {success}/{total} comment(s) posted successfully."
    )
