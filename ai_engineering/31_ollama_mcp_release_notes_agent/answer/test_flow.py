"""Integration & Unit tests for MCP Release Notes Agent.
"""

import json
import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from custom_mcp_server import format_release_note_markdown, save_release_note, OUTPUT_DIR


def test_format_release_note_markdown():
    md = format_release_note_markdown(
        version="v1.0.0",
        title="Initial Launch",
        summary="First official release of the agent.",
        features=["Feature A", "Feature B"],
        fixes=["Fix X"],
    )

    assert "# Release Notes - v1.0.0: Initial Launch" in md
    assert "## 🚀 New Features" in md
    assert "- Feature A" in md
    assert "## 🐛 Bug Fixes & Improvements" in md
    assert "- Fix X" in md


def test_save_release_note():
    res = save_release_note(
        version="v1.1.0",
        title="Performance Patch",
        summary="Improved query latency.",
        features=["Async IO optimization"],
        fixes=["Memory leak fix"],
    )

    assert "Successfully saved release note for v1.1.0" in res
    saved_md = OUTPUT_DIR / "RELEASE_NOTE_v1.1.0.md"
    assert saved_md.exists()
    assert "Async IO optimization" in saved_md.read_text(encoding="utf-8")


if __name__ == "__main__":
    print("Running unit tests...")
    test_format_release_note_markdown()
    print("✅ test_format_release_note_markdown passed!")
    test_save_release_note()
    print("✅ test_save_release_note passed!")
    print("All tests passed successfully!")

