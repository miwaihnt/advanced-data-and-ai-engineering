"""Mock GitHub MCP Server for offline testing and standalone demos.

Provides tool schemas compatible with GitHub MCP Server (PRs and Commit history).
"""

import json
from fastmcp import FastMCP

mcp = FastMCP("MockGitHubMCPServer")


@mcp.tool()
def list_pull_requests(owner: str, repo: str, state: str = "closed") -> str:
    """List recent pull requests for a specified GitHub repository.

    Args:
        owner: Repository owner / organization
        repo: Repository name
        state: State of PRs ('open', 'closed', 'all')

    Returns:
        JSON string containing list of pull requests
    """
    mock_prs = [
        {
            "number": 101,
            "title": "feat: add vector search and hybrid RRF retriever",
            "author": "dev-alpha",
            "state": "merged",
            "merged_at": "2026-08-01T10:00:00Z",
            "body": "Implements hybrid retrieval using reciprocal rank fusion (RRF).",
        },
        {
            "number": 102,
            "title": "fix: handle stream backpressure in FastMCP client",
            "author": "dev-beta",
            "state": "merged",
            "merged_at": "2026-08-03T14:30:00Z",
            "body": "Prevents memory leaks when consuming large SSE event streams.",
        },
        {
            "number": 103,
            "title": "docs: update system architecture diagram for v1.2",
            "author": "tech-lead",
            "state": "merged",
            "merged_at": "2026-08-04T09:15:00Z",
            "body": "Updated architecture.png and added MCP integration steps.",
        },
    ]
    return json.dumps(mock_prs, indent=2)


@mcp.tool()
def get_commit_history(owner: str, repo: str, limit: int = 5) -> str:
    """Get commit history for a GitHub repository.

    Args:
        owner: Repository owner
        repo: Repository name
        limit: Number of recent commits to fetch

    Returns:
        JSON string of commits
    """
    mock_commits = [
        {"sha": "a1b2c3d", "message": "feat: add vector search", "author": "dev-alpha"},
        {"sha": "e5f6g7h", "message": "fix: handle stream backpressure", "author": "dev-beta"},
        {"sha": "i9j0k1l", "message": "docs: update system architecture diagram", "author": "tech-lead"},
    ]
    return json.dumps(mock_commits[:limit], indent=2)


if __name__ == "__main__":
    mcp.run()
