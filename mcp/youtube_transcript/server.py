#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "mcp>=1.0.0",
#     "youtube-transcript-api>=1.2.4",
# ]
# ///
"""MCP server exposing YouTube transcript extraction as a tool."""

from mcp.server.fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

mcp = FastMCP("youtube_transcript")


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


if __name__ == "__main__":
    mcp.run()
