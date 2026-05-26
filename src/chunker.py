"""
chunker.py
----------
Responsible for pre-processing and splitting a raw unified diff into
AI-consumable chunks.

WHY CHUNKING IS NEEDED
----------------------
Large pull requests can produce diffs that are tens or hundreds of thousands
of characters long.  Sending the entire diff in a single API call causes two
problems:

  1. Context-window overflow — most LLMs enforce a hard token (≈ character)
     limit per request.  Exceeding it either truncates the input silently or
     raises an API error, causing missed issues.

  2. Cost and latency — the larger the prompt, the more tokens are billed and
     the longer the model takes to respond.  Chunking lets us process only as
     much text as needed per call and parallelise in the future if required.

The solution is to split the diff into overlapping-free chunks that each stay
below MAX_CHUNK_CHARS, review them independently, and merge the results.

Single responsibility: take a big diff string, return smaller clean chunks.
"""

from src import config


# ---------------------------------------------------------------------------
# Noise filtering
# ---------------------------------------------------------------------------

def filter_noise(diff: str) -> str:
    """
    Remove lines from *diff* that carry no meaningful signal for a code review.

    Filtered-out lines:
      - Whitespace-only additions/deletions  ("+<empty>" or "-<empty>")
        These are blank-line insertions/removals that do not represent logic
        changes and would waste precious token budget.
      - Lines starting with "Binary files"
        Binary diffs (images, compiled artefacts) cannot be reviewed as text.
      - Lines starting with "\\ No newline"
        The "No newline at end of file" git annotation adds noise without
        actionable information.

    Args:
        diff: Raw unified diff string as returned by the GitHub API.

    Returns:
        str: Cleaned diff with noisy lines removed.
    """
    cleaned_lines: list[str] = []

    for line in diff.splitlines():
        # Whitespace-only addition or deletion  ("+  " or "-   " etc.)
        if len(line) >= 1 and line[0] in ("+", "-") and not line[1:].strip():
            continue

        # Binary file notification — not reviewable as text.
        if line.startswith("Binary files"):
            continue

        # Git "no newline at end of file" marker.
        if line.startswith("\\ No newline"):
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_diff(diff: str) -> list[str]:
    """
    Split *diff* into a list of strings, each at most MAX_CHUNK_CHARS long.

    Strategy
    --------
    Lines are grouped greedily: a line is appended to the current chunk as
    long as doing so would not push the chunk past the configured character
    limit.  When a line would overflow the limit, the current chunk is saved
    and a fresh chunk is started with that line.

    This line-boundary approach ensures we never split in the middle of a
    diff hunk header (e.g. "@@ -12,7 +12,9 @@"), keeping each chunk
    self-contained and easier for the AI to reason about.

    Args:
        diff: The diff string to split (ideally already cleaned by
              filter_noise()).

    Returns:
        list[str]: Ordered list of chunk strings ready for AI review.
                   Returns an empty list if *diff* is empty.
    """
    if not diff.strip():
        print("[chunker] Nothing to chunk — diff is empty.")
        return []

    lines: list[str] = diff.splitlines()
    chunks: list[str] = []

    current_lines: list[str] = []
    current_length: int = 0

    for line in lines:
        # +1 accounts for the newline character that joins lines back together.
        line_length = len(line) + 1

        if current_lines and (current_length + line_length) > config.MAX_CHUNK_CHARS:
            # Current chunk is full — save it and start a new one.
            chunks.append("\n".join(current_lines))
            current_lines = []
            current_length = 0

        current_lines.append(line)
        current_length += line_length

    # Append whatever remains in the last (possibly partial) chunk.
    if current_lines:
        chunks.append("\n".join(current_lines))

    print(
        f"[chunker] Split diff into {len(chunks)} chunk(s) "
        f"(limit: {config.MAX_CHUNK_CHARS:,} chars/chunk)."
    )

    return chunks
