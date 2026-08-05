"""Custom MCP Server using FastMCP for Release Notes Management.

This server provides tools and resources for formatting, validating, and saving release notes.
"""

import json
import os
from pathlib import Path
from typing import List, Optional
from fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("ReleaseNotesServer")

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


@mcp.tool()
def format_release_note_markdown(
    version: str,
    title: str,
    summary: str,
    features: Optional[List[str]] = None,
    fixes: Optional[List[str]] = None,
) -> str:
    """Format release note details into a standardized Markdown document.

    Args:
        version: Version string (e.g., 'v1.2.0')
        title: Main title of the release
        summary: High-level summary of the release
        features: List of new feature descriptions
        fixes: List of bug fix descriptions

    Returns:
        Formatted Markdown string
    """
    features_list = features or []
    fixes_list = fixes or []

    md = [
        f"# Release Notes - {version}: {title}",
        "",
        "## 📝 Overview",
        summary,
        "",
    ]

    if features_list:
        md.append("## 🚀 New Features")
        for f in features_list:
            md.append(f"- {f}")
        md.append("")

    if fixes_list:
        md.append("## 🐛 Bug Fixes & Improvements")
        for fx in fixes_list:
            md.append(f"- {fx}")
        md.append("")

    md.append("---")
    md.append("*Generated via Ollama & MCP Release Notes Agent*")

    return "\n".join(md)


@mcp.tool()
def save_release_note(
    version: str,
    title: str,
    summary: str,
    features: Optional[List[str]] = None,
    fixes: Optional[List[str]] = None,
) -> str:
    """Save formatted release notes to local Markdown and JSON files.

    Args:
        version: Version string (e.g., 'v1.2.0')
        title: Main title of the release
        summary: High-level summary of the release
        features: List of new feature descriptions
        fixes: List of bug fix descriptions

    Returns:
        Confirmation message with file path
    """
    md_content = format_release_note_markdown(version, title, summary, features, fixes)

    # Save Markdown file
    clean_version = version.lstrip("v")
    md_filename = f"RELEASE_NOTE_v{clean_version}.md"
    md_path = OUTPUT_DIR / md_filename
    md_path.write_text(md_content, encoding="utf-8")

    # Save JSON database/log
    data = {
        "version": version,
        "title": title,
        "summary": summary,
        "features": features or [],
        "fixes": fixes or [],
        "file_path": str(md_path),
    }

    json_path = OUTPUT_DIR / "release_history.json"
    history = []
    if json_path.exists():
        try:
            history = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            history = []

    history.append(data)
    json_path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")

    return f"Successfully saved release note for {version} to {md_path}"


@mcp.resource("release://templates/standard")
def get_standard_template() -> str:
    """Provide standard template for release notes."""
    return """# Release Notes - [Version]: [Title]

## 📝 Overview
[High-level summary of key changes]

## 🚀 New Features
- [Feature 1]
- [Feature 2]

## 🐛 Bug Fixes & Improvements
- [Fix 1]
- [Fix 2]
"""


@mcp.resource("release://history/latest")
def get_latest_release_history() -> str:
    """Get the latest saved release note JSON from history."""
    json_path = OUTPUT_DIR / "release_history.json"
    if not json_path.exists():
        return json.dumps({"status": "empty", "message": "No release history found."})

    try:
        history = json.loads(json_path.read_text(encoding="utf-8"))
        if not history:
            return json.dumps({"status": "empty", "message": "History is empty."})
        return json.dumps(history[-1], indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    # Run server via stdio transport when executed directly
    mcp.run()
