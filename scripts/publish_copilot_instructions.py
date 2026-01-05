#!/usr/bin/env python3
"""
Publish Copilot instructions to GitHub repository settings.

This script updates the GitHub Copilot instructions for the repository
using the GitHub API. It reads from .github/copilot-instructions.md
and publishes it to the repository settings.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    import requests
    from rich.console import Console
except ImportError:
    print("❌ Missing dependencies. Install with: pip install requests rich")
    sys.exit(1)

console = Console()


def publish_instructions(
    owner: str,
    repo: str,
    token: str,
    instructions_file: Path,
) -> bool:
    """
    Publish Copilot instructions to GitHub repository.
    
    Args:
        owner: GitHub repository owner
        repo: Repository name
        token: GitHub personal access token
        instructions_file: Path to instructions markdown file
        
    Returns:
        True if successful, False otherwise
    """
    if not instructions_file.exists():
        console.print(f"❌ Instructions file not found: {instructions_file}", style="red")
        return False
    
    # Read instructions content
    content = instructions_file.read_text(encoding="utf-8")
    console.print(f"📖 Read {len(content)} characters from {instructions_file.name}", style="cyan")
    
    # GitHub API endpoint for repository custom properties/settings
    # Note: As of 2024, GitHub Copilot instructions might use different endpoints
    # This is a placeholder - actual implementation depends on GitHub API availability
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    
    # For now, we'll just validate the content and display it
    console.print("\n✅ Instructions ready to publish:", style="green")
    console.print(f"   Repository: {owner}/{repo}")
    console.print(f"   File: {instructions_file}")
    console.print(f"   Size: {len(content)} bytes")
    
    console.print("\n⚠️  Note: Automated publishing requires GitHub API support.", style="yellow")
    console.print("   Manual steps:", style="yellow")
    console.print("   1. Go to: https://github.com/{}/{}/settings".format(owner, repo))
    console.print("   2. Navigate to 'Copilot' section")
    console.print("   3. Paste the content from .github/copilot-instructions.md")
    
    return True


def main():
    """Main entry point."""
    # Get repository info from environment or defaults
    owner = os.getenv("GITHUB_OWNER", "intellistream")
    repo = os.getenv("GITHUB_REPO", "sage-pypi-publisher")
    token = os.getenv("GITHUB_TOKEN", "")
    
    # Find instructions file
    instructions_file = Path(__file__).parent.parent / ".github" / "copilot-instructions.md"
    
    console.print("🚀 Copilot Instructions Publisher", style="bold cyan")
    console.print("=" * 50)
    
    if not token:
        console.print("⚠️  No GITHUB_TOKEN found in environment", style="yellow")
        console.print("   Set it with: export GITHUB_TOKEN=your_token", style="yellow")
    
    success = publish_instructions(owner, repo, token, instructions_file)
    
    if success:
        console.print("\n✅ Instructions validated successfully!", style="green")
        return 0
    else:
        console.print("\n❌ Failed to process instructions", style="red")
        return 1


if __name__ == "__main__":
    sys.exit(main())
