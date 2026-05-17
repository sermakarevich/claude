#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "mcp>=1.0.0",
#     "youtube-transcript-api>=1.2.4",
# ]
# ///
"""MCP server exposing YouTube transcript extraction as a tool."""

from pathlib import Path

from mcp.server.fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

INSTRUCTIONS_DIR = Path(__file__).parent / "instructions"


def _instruction_names() -> list[str]:
    if not INSTRUCTIONS_DIR.is_dir():
        return []
    return sorted(p.stem for p in INSTRUCTIONS_DIR.glob("*.md"))


_names = _instruction_names()
_names_hint = f"\n\nAvailable instructions: {', '.join(_names)}." if _names else ""

mcp = FastMCP(
    "youtube_transcript",
    instructions=(
        "Extract YouTube transcripts and run analysis workflows over them. "
        "Transcript tools: `get_transcript`, `get_transcript_with_timestamps`. "
        "Workflow tools: `list_instructions` (enumerate workflows), "
        "`get_instructions` (fetch a workflow's markdown body). "
        f"Workflow files live in `{INSTRUCTIONS_DIR}`."
        + _names_hint
    ),
)


def _extract_video_id(url_or_id: str) -> str:
    if "youtube.com/watch?v=" in url_or_id:
        return url_or_id.split("v=")[1].split("&")[0]
    if "youtu.be/" in url_or_id:
        return url_or_id.split("youtu.be/")[1].split("?")[0]
    return url_or_id


@mcp.tool()
def get_transcript(video: str, languages: list[str] | None = None) -> str:
    """Extract the full transcript text from a YouTube video.

    Args:
        video: YouTube URL (youtube.com/watch?v=..., youtu.be/...) or bare video ID.
        languages: Language codes in preference order (default: ["en"]).

    Returns:
        The full transcript text as a single space-joined string, or an
        error message if the transcript is unavailable.
    """
    if languages is None:
        languages = ["en"]
    video_id = _extract_video_id(video)
    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=languages)
        return " ".join(snippet.text for snippet in transcript.snippets)
    except TranscriptsDisabled:
        return f"Error: transcripts are disabled for video '{video_id}'"
    except NoTranscriptFound:
        return f"Error: no transcript found for video '{video_id}' in languages {languages}"


@mcp.tool()
def get_transcript_with_timestamps(video: str, languages: list[str] | None = None) -> list[dict]:
    """Extract the transcript with per-snippet timestamps.

    Args:
        video: YouTube URL or bare video ID.
        languages: Language codes in preference order (default: ["en"]).

    Returns:
        List of {"text": str, "start": float, "duration": float} entries.
    """
    if languages is None:
        languages = ["en"]
    video_id = _extract_video_id(video)
    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id, languages=languages)
    return [
        {"text": s.text, "start": s.start, "duration": s.duration}
        for s in transcript.snippets
    ]


@mcp.tool()
def list_instructions() -> list[str]:
    """List the names of available analysis workflows.

    Returns:
        Workflow names (filename stems of `.md` files in the instructions folder).
        Pass any of these to `get_instructions` to fetch the full markdown body.
    """
    return _instruction_names()


@mcp.tool()
def get_instructions(name: str) -> str:
    """Fetch the markdown body of a named analysis workflow.

    Args:
        name: Workflow name as returned by `list_instructions` (filename stem,
            without the `.md` extension).

    Returns:
        The raw markdown content, or an error message if the workflow is missing.
    """
    path = INSTRUCTIONS_DIR / f"{name}.md"
    if not path.is_file():
        available = ", ".join(_instruction_names()) or "(none)"
        return f"Error: instructions '{name}' not found. Available: {available}"
    return path.read_text()


if __name__ == "__main__":
    mcp.run()
