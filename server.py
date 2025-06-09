
from typing import Any, Dict, Optional, List
import httpx
import json
import base64
from mcp.server.fastmcp import FastMCP
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP(
    name="gitHub",
    host="0.0.0.0",
    port=8080,
    path="/mcp"
)

# Constants
GITHUB_API_BASE = "https://api.github.com"
USER_AGENT = "github-mcp-app/1.0"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


async def make_github_request(
    url: str,
    method: str = "GET",
    json: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Make a request to the GitHub API with error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github.v3+json",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(method, url, headers=headers, json=json, timeout=30.0)
            response.raise_for_status()
            return response.json() if response.content else {}
        except Exception as e:
            # Log or handle the error as needed
            return {"error": f"GitHub API request failed: {str(e)}"}


def format_repository(repo: Dict[str, Any]) -> str:
    """Format a GitHub repository into a readable string."""
    return (
        f"Name: {repo.get('full_name', 'Unknown')}\n"
        f"Description: {repo.get('description', 'No description')}\n"
        f"Stars: {repo.get('stargazers_count', 0)}\n"
        f"URL: {repo.get('html_url', 'No URL')}"
    )


def format_issue(issue: Dict[str, Any]) -> str:
    """Format a GitHub issue into a readable string."""
    return (
        f"Issue #{issue.get('number', 'Unknown')}\n"
        f"Title: {issue.get('title', 'No title')}\n"
        f"State: {issue.get('state', 'Unknown')}\n"
        f"URL: {issue.get('html_url', 'No URL')}"
    )


def format_pull_request(pr: Dict[str, Any]) -> str:
    """Format a GitHub pull request into a readable string."""
    return (
        f"PR #{pr.get('number', 'Unknown')}\n"
        f"Title: {pr.get('title', 'No title')}\n"
        f"State: {pr.get('state', 'Unknown')}\n"
        f"URL: {pr.get('html_url', 'No URL')}"
    )


def format_branch(branch: Dict[str, Any]) -> str:
    """Format a GitHub branch into a readable string."""
    return (
        f"Name: {branch.get('name', 'Unknown')}\n"
        f"SHA: {branch.get('commit', {}).get('sha', 'Unknown')}\n"
        f"URL: {branch.get('_links', {}).get('html', 'No URL')}"
    )


def format_webhook(webhook: Dict[str, Any]) -> str:
    """Format a GitHub webhook into a readable string."""
    return (
        f"ID: {webhook.get('id', 'Unknown')}\n"
        f"Type: {webhook.get('type', 'Unknown')}\n"
        f"Events: {', '.join(webhook.get('events', []))}\n"
        f"URL: {webhook.get('config', {}).get('url', 'No URL')}\n"
        f"Active: {webhook.get('active', False)}"
    )


@mcp.tool()
async def search_repositories(query: str, per_page: int = 30, page: int = 1) -> str:
    """
    Search GitHub repositories by query.

    Args:
        query: Search keywords.
        per_page: Number of results per page (max 100).
        page: Page number.
    """
    url = f"{GITHUB_API_BASE}/search/repositories?q={query}&per_page={per_page}&page={page}"
    data = await make_github_request(url)

    if not data or "items" not in data:
        return "Unable to fetch repositories or no repositories found."

    if not data["items"]:
        return "No repositories found for this query."

    repos = [format_repository(repo) for repo in data["items"]]
    return "\n---\n".join(repos)


@mcp.tool()
async def create_issue(owner: str, repo: str, title: str, body: str) -> str:
    """
    Create a GitHub issue.

    Args:
        owner: Repository owner.
        repo: Repository name.
        title: Issue title.
        body: Issue description.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues"
    payload = {"title": title, "body": body}
    data = await make_github_request(url, method="POST", json=payload)

    if not data or "error" in data:
        return f"Unable to create issue: {data.get('error', 'Unknown error')}"

    return format_issue(data)


# Repository Management Tools
@mcp.tool()
async def create_repository(name: str, description: str = "", private: bool = False) -> str:
    """
    Create a new GitHub repository.

    Args:
        name: Repository name.
        description: Repository description.
        private: Whether the repository should be private.
    """
    url = f"{GITHUB_API_BASE}/user/repos"
    payload = {
        "name": name,
        "description": description,
        "private": private,
        "auto_init": True
    }
    data = await make_github_request(url, method="POST", json=payload)

    if not data or "error" in data:
        return f"Unable to create repository: {data.get('error', 'Unknown error')}"

    return format_repository(data)


@mcp.tool()
async def delete_repository(owner: str, repo: str) -> str:
    """
    Delete a GitHub repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    data = await make_github_request(url, method="DELETE")

    if data and "error" in data:
        return f"Unable to delete repository: {data.get('error', 'Unknown error')}"

    return f"Repository {owner}/{repo} deleted successfully."


# Branch Management Tools
@mcp.tool()
async def list_branches(owner: str, repo: str) -> str:
    """
    List branches in a GitHub repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/branches"
    data = await make_github_request(url)

    if not data or "error" in data:
        return f"Unable to list branches: {data.get('error', 'Unknown error')}"

    if not data:
        return "No branches found."

    branches = [format_branch(branch) for branch in data]
    return "\n---\n".join(branches)


@mcp.tool()
async def create_branch(owner: str, repo: str, branch_name: str, source_branch: str = "main") -> str:
    """
    Create a new branch in a GitHub repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        branch_name: Name for the new branch.
        source_branch: Source branch to create from.
    """
    # Get the SHA of the source branch
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/refs/heads/{source_branch}"
    data = await make_github_request(url)

    if not data or "error" in data:
        return f"Unable to get source branch: {data.get('error', 'Unknown error')}"

    sha = data.get("object", {}).get("sha")
    if not sha:
        return "Unable to get source branch SHA."

    # Create the new branch
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/refs"
    payload = {
        "ref": f"refs/heads/{branch_name}",
        "sha": sha
    }
    data = await make_github_request(url, method="POST", json=payload)

    if not data or "error" in data:
        return f"Unable to create branch: {data.get('error', 'Unknown error')}"

    return f"Branch '{branch_name}' created successfully from '{source_branch}'."


@mcp.tool()
async def delete_branch(owner: str, repo: str, branch_name: str) -> str:
    """
    Delete a branch in a GitHub repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        branch_name: Name of the branch to delete.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/refs/heads/{branch_name}"
    data = await make_github_request(url, method="DELETE")

    if data and "error" in data:
        return f"Unable to delete branch: {data.get('error', 'Unknown error')}"

    return f"Branch '{branch_name}' deleted successfully."


# File Management Tools
@mcp.tool()
async def create_or_update_file(owner: str, repo: str, path: str, content: str, message: str, branch: str = "main") -> str:
    """
    Create or update a file in a GitHub repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        path: File path in the repository.
        content: File content.
        message: Commit message.
        branch: Branch name.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
    
    # Check if file exists
    existing_file = await make_github_request(url, params={"ref": branch})
    
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
        "branch": branch
    }
    
    # If file exists, we need to include the SHA
    if existing_file and not "error" in existing_file:
        payload["sha"] = existing_file.get("sha")
    
    data = await make_github_request(url, method="PUT", json=payload)
    
    if not data or "error" in data:
        return f"Unable to create/update file: {data.get('error', 'Unknown error')}"
    
    return f"File '{path}' created/updated successfully in branch '{branch}'."


# Pull Request Tools
@mcp.tool()
async def create_pull_request(owner: str, repo: str, title: str, head: str, base: str = "main", body: str = "") -> str:
    """
    Create a pull request in a GitHub repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        title: Pull request title.
        head: The name of the branch where changes are implemented.
        base: The name of the branch you want the changes pulled into.
        body: Pull request description.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls"
    payload = {
        "title": title,
        "head": head,
        "base": base,
        "body": body
    }
    data = await make_github_request(url, method="POST", json=payload)

    if not data or "error" in data:
        return f"Unable to create pull request: {data.get('error', 'Unknown error')}"

    return format_pull_request(data)


@mcp.tool()
async def list_pull_requests(owner: str, repo: str, state: str = "open") -> str:
    """
    List pull requests in a GitHub repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        state: Pull request state (open, closed, all).
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls"
    params = {"state": state}
    data = await make_github_request(url, params=params)

    if not data or "error" in data:
        return f"Unable to list pull requests: {data.get('error', 'Unknown error')}"

    if not data:
        return f"No {state} pull requests found."

    prs = [format_pull_request(pr) for pr in data]
    return "\n---\n".join(prs)


@mcp.tool()
async def merge_pull_request(owner: str, repo: str, pull_number: int, commit_title: str = "") -> str:
    """
    Merge a pull request in a GitHub repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        pull_number: Pull request number.
        commit_title: Title for the merge commit.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pull_number}/merge"
    payload = {}
    if commit_title:
        payload["commit_title"] = commit_title

    data = await make_github_request(url, method="PUT", json=payload)

    if not data or "error" in data:
        return f"Unable to merge pull request: {data.get('error', 'Unknown error')}"

    return f"Pull request #{pull_number} merged successfully."


# Webhook Management Tools
@mcp.tool()
async def create_webhook(owner: str, repo: str, url: str, events: List[str] = ["push"]) -> str:
    """
    Create a webhook in a GitHub repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        url: Webhook payload URL.
        events: Events that trigger the webhook.
    """
    api_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/hooks"
    payload = {
        "config": {
            "url": url,
            "content_type": "json"
        },
        "events": events,
        "active": True
    }
    data = await make_github_request(api_url, method="POST", json=payload)

    if not data or "error" in data:
        return f"Unable to create webhook: {data.get('error', 'Unknown error')}"

    return format_webhook(data)


@mcp.tool()
async def list_webhooks(owner: str, repo: str) -> str:
    """
    List webhooks in a GitHub repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/hooks"
    data = await make_github_request(url)

    if not data or "error" in data:
        return f"Unable to list webhooks: {data.get('error', 'Unknown error')}"

    if not data:
        return "No webhooks found."

    webhooks = [format_webhook(webhook) for webhook in data]
    return "\n---\n".join(webhooks)


@mcp.tool()
async def delete_webhook(owner: str, repo: str, webhook_id: int) -> str:
    """
    Delete a webhook in a GitHub repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        webhook_id: Webhook ID.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/hooks/{webhook_id}"
    data = await make_github_request(url, method="DELETE")

    if data and "error" in data:
        return f"Unable to delete webhook: {data.get('error', 'Unknown error')}"

    return f"Webhook {webhook_id} deleted successfully."


# GitHub Actions Tools
@mcp.tool()
async def list_workflow_runs(owner: str, repo: str, workflow_id: str = None) -> str:
    """
    List GitHub Actions workflow runs.

    Args:
        owner: Repository owner.
        repo: Repository name.
        workflow_id: Optional workflow ID to filter by.
    """
    base_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/actions/runs"
    url = f"{base_url}/{workflow_id}/runs" if workflow_id else base_url
    
    data = await make_github_request(url)

    if not data or "error" in data:
        return f"Unable to list workflow runs: {data.get('error', 'Unknown error')}"

    if not data.get("workflow_runs", []):
        return "No workflow runs found."

    runs = []
    for run in data.get("workflow_runs", [])[:10]:  # Limit to 10 runs
        runs.append(
            f"Run #{run.get('id')}\n"
            f"Name: {run.get('name')}\n"
            f"Status: {run.get('status')}\n"
            f"Conclusion: {run.get('conclusion')}\n"
            f"URL: {run.get('html_url')}"
        )
    
    return "\n---\n".join(runs)


if __name__ == "__main__":
    # Run the MCP server with streamable-http transport
    mcp.run(transport="streamable-http")
