"""
main.py
-------
Entry point for the AI Code Reviewer pipeline.

This file contains ZERO business logic.  Its only job is to wire the
individual modules together in the correct order, like stages in a pipeline:

    GitHub API  →  Diff  →  Chunks  →  AI Review  →  GitHub Comments

Each stage is handled entirely by its own module (fetcher, chunker,
reviewer, commenter).  main() just calls them in sequence and prints
banners so CI logs are easy to read at a glance.
"""

from src import config
from src.fetcher   import fetch_diff
from src.chunker   import chunk_diff, filter_noise
from src.reviewer  import review_all_chunks
from src.commenter import post_all_comments


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Run the full AI code-review pipeline from diff fetch to comment posting.
    """

    # -------------------------------------------------------------------------
    # Step 1 — Startup banner
    # -------------------------------------------------------------------------
    print("=" * 60)
    print("  AI CODE REVIEWER — Starting")
    print("=" * 60)

    # -------------------------------------------------------------------------
    # Step 2 — Validate environment variables
    # Raises EnvironmentError with clear messages if anything is missing,
    # stopping the pipeline before any API calls are made.
    # -------------------------------------------------------------------------
    print("\n[main] Step 2 — Validating configuration ...")
    config.validate()
    print("[main] Configuration OK.")

    # -------------------------------------------------------------------------
    # Step 3 — Fetch the pull-request diff from GitHub
    # An empty diff means the PR has no file changes; nothing to review.
    # -------------------------------------------------------------------------
    print("\n[main] Step 3 — Fetching pull-request diff ...")
    raw_diff: str = fetch_diff()

    if not raw_diff:
        print("[main] WARNING: Diff is empty — no changes to review. Exiting.")
        return

    # -------------------------------------------------------------------------
    # Step 4 — Clean and chunk the diff
    # filter_noise() removes whitespace-only and binary lines.
    # chunk_diff() splits the cleaned diff into AI-safe pieces.
    # -------------------------------------------------------------------------
    print("\n[main] Step 4 — Filtering noise and chunking diff ...")
    cleaned_diff: str       = filter_noise(raw_diff)
    chunks:       list[str] = chunk_diff(cleaned_diff)

    # -------------------------------------------------------------------------
    # Step 5 — Send each chunk to the AI for review
    # review_all_chunks() handles progress printing and error recovery.
    # -------------------------------------------------------------------------
    print("\n[main] Step 5 — Reviewing chunks with AI ...")
    issues: list[dict] = review_all_chunks(chunks)

    # -------------------------------------------------------------------------
    # Step 6 — Post results as GitHub PR comments
    # post_all_comments() handles both the "issues found" and "clean" cases.
    # -------------------------------------------------------------------------
    print("\n[main] Step 6 — Posting comments to GitHub ...")
    post_all_comments(issues)

    # -------------------------------------------------------------------------
    # Step 7 — Completion banner
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  AI CODE REVIEWER — Done!")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
