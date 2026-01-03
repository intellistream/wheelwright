"""Git hooks management for sage-pypi-publisher."""
from __future__ import annotations

import os
import stat
from pathlib import Path

from rich.console import Console

console = Console()

PRE_PUSH_HOOK_TEMPLATE = '''#!/bin/bash
# Pre-push hook managed by sage-pypi-publisher
# Auto-detects version updates and offers to build/upload to PyPI

set -e

# Colors
RED='\\033[0;31m'
YELLOW='\\033[1;33m'
GREEN='\\033[0;32m'
CYAN='\\033[0;36m'
BLUE='\\033[0;34m'
NC='\\033[0m'

CURRENT_VERSION=$(grep -oP '^version = "\\K[^"]+' pyproject.toml 2>/dev/null || echo "unknown")

if [ "$CURRENT_VERSION" = "unknown" ]; then
    echo -e "${YELLOW}No pyproject.toml found, skipping version check${NC}"
    exit 0
fi

if ! git rev-parse HEAD~1 >/dev/null 2>&1; then
    echo -e "${YELLOW}First commit detected, skipping version check${NC}"
    exit 0
fi

VERSION_UPDATED=false
for i in {1..5}; do
    if git diff HEAD~$i HEAD -- pyproject.toml 2>/dev/null | grep -q '^[+-]version = '; then
        VERSION_UPDATED=true
        break
    fi
done

if [ "$VERSION_UPDATED" = true ]; then
    echo -e "${GREEN}✓ Version updated to ${CURRENT_VERSION}${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}📦 Build and upload version ${CURRENT_VERSION} to PyPI?${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${GREEN}[y]${NC} Yes, build and upload to PyPI"
    echo -e "  ${YELLOW}[n]${NC} No, just push to GitHub"
    echo -e "  ${RED}[c]${NC} Cancel push"
    echo -n "Your choice [y/n/c]: "
    read -r response </dev/tty
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}🔨 Building package...${NC}"
        rm -rf dist/ wheelhouse/ 2>/dev/null || true
        
        if command -v sage-pypi-publisher &> /dev/null; then
            echo -e "${GREEN}Using sage-pypi-publisher (auto-detects build type)...${NC}"
            if sage-pypi-publisher build . --upload --no-dry-run; then
                echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                echo -e "${GREEN}✓ Successfully uploaded ${CURRENT_VERSION} to PyPI${NC}"
                echo -e "${GREEN}🔗 https://pypi.org/project/{package_name}/${CURRENT_VERSION}/${NC}"
                echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            else
                echo -e "${RED}✗ Failed to upload to PyPI${NC}"
                echo -e "${YELLOW}Continue push anyway? [y/N]${NC}"
                read -r cont </dev/tty
                [[ ! "$cont" =~ ^[Yy]$ ]] && exit 1
            fi
        else
            echo -e "${YELLOW}⚠ sage-pypi-publisher not found${NC}"
            echo -e "${YELLOW}Install: pip install sage-pypi-publisher${NC}"
            echo -e "${YELLOW}Continue push? [y/N]${NC}"
            read -r cont </dev/tty
            [[ ! "$cont" =~ ^[Yy]$ ]] && exit 1
        fi
    elif [[ "$response" =~ ^[Cc]$ ]]; then
        echo -e "${YELLOW}Push cancelled${NC}"
        exit 1
    else
        echo -e "${YELLOW}Skipping PyPI upload${NC}"
    fi
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}⚠  WARNING: Version not updated!${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}📌 Current version: ${BLUE}${CURRENT_VERSION}${NC}"
    echo ""
    echo -e "${BLUE}What would you like to do?${NC}"
    echo -e "  ${GREEN}[u]${NC} Update version now (interactive)"
    echo -e "  ${YELLOW}[y]${NC} Continue without version update"
    echo -e "  ${RED}[n]${NC} Cancel push"
    echo -n "Your choice [u/y/n]: "
    read -r response </dev/tty
    
    if [[ "$response" =~ ^[Uu]$ ]]; then
        echo ""
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BLUE}📝 Version Update${NC}"
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${YELLOW}Current: ${BLUE}${CURRENT_VERSION}${NC}"
        echo ""
        echo -e "${GREEN}Enter new version (e.g., 0.1.4, 1.0.0):${NC}"
        echo -n "New version: "
        read -r new_version </dev/tty
        
        if [[ ! "$new_version" =~ ^[0-9]+\\.[0-9]+\\.[0-9]+([a-zA-Z0-9._-]+)?$ ]]; then
            echo -e "${RED}✗ Invalid format. Expected: X.Y.Z${NC}"
            exit 1
        fi
        
        sed -i "s/version = \\"${CURRENT_VERSION}\\"/version = \\"${new_version}\\"/" pyproject.toml
        git add pyproject.toml
        git commit -m "chore: bump version to ${new_version}"
        
        echo ""
        echo -e "${GREEN}✓ ${BLUE}${CURRENT_VERSION}${GREEN} → ${BLUE}${new_version}${NC}"
        echo ""
        echo -e "${BLUE}📦 Build and upload to PyPI? [y/n]:${NC} "
        read -r upload_resp </dev/tty
        
        if [[ "$upload_resp" =~ ^[Yy]$ ]]; then
            rm -rf dist/ wheelhouse/ 2>/dev/null || true
            if command -v sage-pypi-publisher &> /dev/null; then
                sage-pypi-publisher build . --upload --no-dry-run
                echo -e "${GREEN}✓ Uploaded ${new_version} to PyPI${NC}"
            fi
        fi
        exit 0
    elif [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Continuing without version update${NC}"
    else
        echo -e "${YELLOW}Push cancelled${NC}"
        exit 1
    fi
fi

exit 0
'''


def install_git_hooks(package_path: Path | None = None) -> bool:
    """
    Install sage-pypi-publisher git hooks into the current repository.
    
    Args:
        package_path: Path to the package directory. If None, uses current directory.
        
    Returns:
        True if successful, False otherwise
    """
    if package_path is None:
        package_path = Path.cwd()
    else:
        package_path = Path(package_path)
    
    # Find .git directory
    git_dir = package_path / ".git"
    if not git_dir.exists():
        console.print("[red]✗ Not a git repository[/red]")
        console.print("[yellow]Run 'git init' first[/yellow]")
        return False
    
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    
    # Get package name from pyproject.toml
    pyproject_file = package_path / "pyproject.toml"
    package_name = "your-package"
    if pyproject_file.exists():
        try:
            import tomli
        except ImportError:
            try:
                import tomllib as tomli  # type: ignore
            except ImportError:
                tomli = None
        
        if tomli:
            try:
                with open(pyproject_file, "rb") as f:
                    data = tomli.load(f)
                    package_name = data.get("project", {}).get("name", "your-package")
            except Exception:
                pass
    
    # Create pre-push hook
    pre_push_hook = hooks_dir / "pre-push"
    hook_content = PRE_PUSH_HOOK_TEMPLATE.replace("{package_name}", package_name)
    
    # Backup existing hook if it exists
    if pre_push_hook.exists():
        backup_path = hooks_dir / "pre-push.backup"
        console.print(f"[yellow]Backing up existing hook to {backup_path.name}[/yellow]")
        import shutil
        shutil.copy(pre_push_hook, backup_path)
    
    # Write new hook
    pre_push_hook.write_text(hook_content, encoding="utf-8")
    
    # Make executable
    current_permissions = pre_push_hook.stat().st_mode
    pre_push_hook.chmod(current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    
    console.print("[green]✓ Git hooks installed successfully[/green]")
    console.print(f"[cyan]Location: {pre_push_hook}[/cyan]")
    console.print("\n[bold]Hook features:[/bold]")
    console.print("  • Auto-detects version updates")
    console.print("  • Interactive version bumping")
    console.print("  • Automatic PyPI upload with sage-pypi-publisher")
    console.print("  • Smart build type detection (manylinux for C++ extensions)")
    
    return True


def uninstall_git_hooks(package_path: Path | None = None) -> bool:
    """
    Uninstall sage-pypi-publisher git hooks.
    
    Args:
        package_path: Path to the package directory. If None, uses current directory.
        
    Returns:
        True if successful, False otherwise
    """
    if package_path is None:
        package_path = Path.cwd()
    else:
        package_path = Path(package_path)
    
    git_dir = package_path / ".git"
    if not git_dir.exists():
        console.print("[red]✗ Not a git repository[/red]")
        return False
    
    pre_push_hook = git_dir / "hooks" / "pre-push"
    
    if not pre_push_hook.exists():
        console.print("[yellow]No pre-push hook found[/yellow]")
        return False
    
    # Check if it's our hook
    content = pre_push_hook.read_text(encoding="utf-8")
    if "sage-pypi-publisher" not in content:
        console.print("[yellow]Pre-push hook is not managed by sage-pypi-publisher[/yellow]")
        console.print("[yellow]Remove it manually if needed[/yellow]")
        return False
    
    # Check for backup
    backup_path = git_dir / "hooks" / "pre-push.backup"
    if backup_path.exists():
        console.print("[cyan]Restoring backup...[/cyan]")
        import shutil
        shutil.copy(backup_path, pre_push_hook)
        backup_path.unlink()
        console.print("[green]✓ Restored previous hook from backup[/green]")
    else:
        pre_push_hook.unlink()
        console.print("[green]✓ Removed pre-push hook[/green]")
    
    return True
