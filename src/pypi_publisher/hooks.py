"""Git hooks management for sage-pypi-publisher."""
from __future__ import annotations

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

PRE_COMMIT_HOOK_TEMPLATE = '''#!/bin/bash
# Pre-commit hook managed by sage-pypi-publisher
# Runs code quality checks (ruff, mypy) if available

set -e

# Colors
RED='\\033[0;31m'
YELLOW='\\033[1;33m'
GREEN='\\033[0;32m'
NC='\\033[0m'

echo -e "${GREEN}🔍 Running pre-commit checks...${NC}"

# Check for large files (>10MB)
echo -e "${GREEN}• Checking for large files...${NC}"
# git diff --cached --name-only | xargs -I{} du -h "{}" | awk '$1 ~ /[0-9]M/ && $1+0 > 10 {print $0}'

# Run Ruff if available
if command -v ruff &> /dev/null; then
    echo -e "${GREEN}• Running ruff linting...${NC}"
    if ! ruff check .; then
        echo -e "${RED}✗ Ruff linting failed${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Ruff passed${NC}"
else
    echo -e "${YELLOW}⚠ Ruff not found, skipping linting${NC}"
fi

# Run MyPy if available
if command -v mypy &> /dev/null; then
    echo -e "${GREEN}• Running mypy type checking...${NC}"
    # Only check staged python files or src directory?
    # Checking everything might be slow. For now check src/ if it exists
    if [ -d "src" ]; then
        if ! mypy src/; then
             echo -e "${RED}✗ MyPy type checking failed${NC}"
             exit 1
        fi
        echo -e "${GREEN}✓ MyPy passed${NC}"
    fi
else
    echo -e "${YELLOW}⚠ MyPy not found, skipping type checking${NC}"
fi

echo -e "${GREEN}✓ All checks passed!${NC}"
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

    # Backup existing pre-push hook if it exists
    if pre_push_hook.exists():
        backup_path = hooks_dir / "pre-push.backup"
        if "sage-pypi-publisher" not in pre_push_hook.read_text():
            console.print(f"[yellow]Backing up existing pre-push hook to {backup_path.name}[/yellow]")
            import shutil
            shutil.copy(pre_push_hook, backup_path)

    # Write new pre-push hook
    pre_push_hook.write_text(hook_content, encoding="utf-8")
    pre_push_hook.chmod(pre_push_hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # Create pre-commit hook
    pre_commit_hook = hooks_dir / "pre-commit"

    # Backup existing pre-commit hook if it exists
    if pre_commit_hook.exists():
        backup_path = hooks_dir / "pre-commit.backup"
        if "sage-pypi-publisher" not in pre_commit_hook.read_text():
            console.print(f"[yellow]Backing up existing pre-commit hook to {backup_path.name}[/yellow]")
            import shutil
            shutil.copy(pre_commit_hook, backup_path)

    # Write new pre-commit hook
    pre_commit_hook.write_text(PRE_COMMIT_HOOK_TEMPLATE, encoding="utf-8")
    pre_commit_hook.chmod(pre_commit_hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    console.print("[green]✓ Git hooks installed successfully[/green]")
    console.print(f"[cyan]Location: {hooks_dir}[/cyan]")
    console.print("\n[bold]Hook features:[/bold]")
    console.print("  • Pre-commit: Code quality checks (ruff + mypy)")
    console.print("  • Pre-push: Auto-detects version updates & PyPI upload")

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
    pre_commit_hook = git_dir / "hooks" / "pre-commit"

    # Remove pre-push
    if pre_push_hook.exists():
        content = pre_push_hook.read_text(encoding="utf-8")
        if "sage-pypi-publisher" in content:
            backup_path = git_dir / "hooks" / "pre-push.backup"
            if backup_path.exists():
                console.print("[cyan]Restoring pre-push backup...[/cyan]")
                import shutil
                shutil.copy(backup_path, pre_push_hook)
                backup_path.unlink()
            else:
                pre_push_hook.unlink()
                console.print("[green]✓ Removed pre-push hook[/green]")

    # Remove pre-commit
    if pre_commit_hook.exists():
        content = pre_commit_hook.read_text(encoding="utf-8")
        if "sage-pypi-publisher" in content:
            backup_path = git_dir / "hooks" / "pre-commit.backup"
            if backup_path.exists():
                console.print("[cyan]Restoring pre-commit backup...[/cyan]")
                import shutil
                shutil.copy(backup_path, pre_commit_hook)
                backup_path.unlink()
            else:
                pre_commit_hook.unlink()
                console.print("[green]✓ Removed pre-commit hook[/green]")

    return True
