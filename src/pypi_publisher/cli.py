"""Command line interface for sage-pypi-publisher."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from pypi_publisher.compiler import BytecodeCompiler
from pypi_publisher.manylinux_builder import ManylinuxBuilder
from pypi_publisher.detector import detect_build_system
from pypi_publisher._version import __version__
import requests
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

console = Console()
app = typer.Typer(name="sage-pypi-publisher", add_completion=False, no_args_is_help=True)


@app.command()
def compile(
    package_path: Path = typer.Argument(..., help="Path to the package directory containing pyproject.toml"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory for compiled package"),
):
    """Compile a package to bytecode (py -> pyc) in a copied tree."""
    compiler = BytecodeCompiler(package_path)
    compiled = compiler.compile_package(output_dir)
    console.print(f"[bold green]✓ 编译完成: {compiled}[/bold green]")


@app.command()
def build(
    package_path: Path = typer.Argument(..., help="Path to the package directory"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory"),
    upload: bool = typer.Option(False, "--upload", "-u", help="Upload after build"),
    repository: str = typer.Option("pypi", "--repository", "-r", help="pypi or testpypi"),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Skip actual upload when true"),
    force_manylinux: bool = typer.Option(False, "--force-manylinux", help="Force manylinux build"),
    force_bytecode: bool = typer.Option(False, "--force-bytecode", help="Force bytecode compilation"),
    platform_tag: str = typer.Option("manylinux_2_34_x86_64", "--platform", "-p", help="Manylinux platform tag (for extension packages)"),
):
    """
    Smart build: auto-detects package type and builds appropriately.
    
    - C/C++ extension packages → manylinux wheel
    - Pure Python packages → bytecode compilation
    
    Use --force-manylinux or --force-bytecode to override auto-detection.
    """
    build_system = detect_build_system(package_path)
    
    if force_manylinux:
        build_system = "extension"
    elif force_bytecode:
        build_system = "pure-python"
    
    console.print(f"�� Detected build system: [cyan]{build_system}[/cyan]")
    
    if build_system == "extension":
        # Build manylinux wheel for C/C++ extensions
        console.print("🔧 Building as C/C++ extension package with manylinux tags...")
        builder = ManylinuxBuilder(package_path)
        wheel_path = builder.build_manylinux_wheel(
            output_dir=output_dir,
            platform_tag=platform_tag,
        )
        console.print(f"[bold green]✓ 构建成功: {wheel_path.name}[/bold green]")
    else:
        # Build bytecode-compiled wheel for pure Python
        console.print("🔧 Building as pure Python package with bytecode compilation...")
        compiler = BytecodeCompiler(package_path)
        compiled = compiler.compile_package(output_dir)
        wheel_path = compiler.build_wheel(compiled)
        console.print(f"[bold green]✓ 构建成功: {wheel_path}[/bold green]")
    
    if upload:
        compiler = BytecodeCompiler(package_path)
        compiler.upload_wheel(wheel_path, repository=repository, dry_run=dry_run)


@app.command("build-manylinux")
def build_manylinux(
    package_path: Path = typer.Argument(..., help="Path to the package directory"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory (default: ./wheelhouse)"),
    platform_tag: str = typer.Option("manylinux_2_34_x86_64", "--platform", "-p", help="Manylinux platform tag"),
    upload: bool = typer.Option(False, "--upload", "-u", help="Upload after build"),
    repository: str = typer.Option("pypi", "--repository", "-r", help="pypi or testpypi"),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Skip actual upload when true"),
):
    """
    Build manylinux wheel for C/C++ extension packages.
    
    This is useful for packages with C/C++ extensions that have external
    dependencies (like MKL, FAISS, CUDA) which can't be bundled by auditwheel.
    The wheel will be built with the specified manylinux platform tag.
    
    Examples:
        # Build a manylinux wheel
        sage-pypi-publisher build-manylinux .
        
        # Build and upload (real upload)
        sage-pypi-publisher build-manylinux . --upload --no-dry-run
        
        # Use a specific platform tag
        sage-pypi-publisher build-manylinux . --platform manylinux_2_28_x86_64
    """
    builder = ManylinuxBuilder(package_path)
    wheel_path = builder.build_manylinux_wheel(
        output_dir=output_dir,
        platform_tag=platform_tag,
    )
    
    console.print(f"[bold green]✓ Manylinux wheel created: {wheel_path.name}[/bold green]")
    
    if upload:
        from pypi_publisher.compiler import BytecodeCompiler
        compiler = BytecodeCompiler(package_path)
        compiler.upload_wheel(wheel_path, repository=repository, dry_run=dry_run)


@app.command()
def upload(
    wheel_path: Path = typer.Argument(..., help="Wheel file to upload"),
    repository: str = typer.Option("pypi", "--repository", "-r", help="pypi or testpypi"),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Skip actual upload when true"),
):
    """Upload an existing wheel file via twine."""
    compiler = BytecodeCompiler(package_path=wheel_path.parent)
    compiler.upload_wheel(wheel_path, repository=repository, dry_run=dry_run)


@app.callback()
def version_callback(version: bool = typer.Option(False, "--version", callback=None, is_eager=True, help="Show version and exit")):
    if version:
        console.print(f"sage-pypi-publisher {__version__}")
        raise typer.Exit(0)




@app.command()
def install_hooks(
    package_path: Path = typer.Argument(".", help="Path to the package directory"),
):
    """Install sage-pypi-publisher git hooks (pre-push) into your repository."""
    from pypi_publisher.hooks import install_git_hooks
    
    console.print("[bold]Installing git hooks...[/bold]")
    success = install_git_hooks(package_path)
    
    if success:
        console.print("\n[green]✓ Ready to use![/green]")
        console.print("\n[bold]Next time you push:[/bold]")
        console.print("  1. Update version in pyproject.toml")
        console.print("  2. git commit -m 'chore: bump version'")
        console.print("  3. git push")
        console.print("  4. Hook will detect version change and offer to upload to PyPI!")
        console.print("\n[dim]Or choose [u]pdate interactively if you forget to bump version[/dim]")


@app.command()
def uninstall_hooks(
    package_path: Path = typer.Argument(".", help="Path to the package directory"),
):
    """Uninstall sage-pypi-publisher git hooks."""
    from pypi_publisher.hooks import uninstall_git_hooks
    
    console.print("[bold]Uninstalling git hooks...[/bold]")
    uninstall_git_hooks(package_path)


def find_monorepo_packages(root: Path) -> list[str]:
    """Find all packages in the monorepo by looking for pyproject.toml files."""
    packages = []
    # Use glob to find pyproject.toml files
    # Exclude common ignore dirs manually for speed if needed, but rglob is okay for reasonable size
    # We'll skip directories starting with . or _ or build/dist/venv
    
    console.print(f"[dim]Scanning {root} for python packages...[/dim]")
    
    for path in root.rglob("pyproject.toml"):
        # Skip if in hidden dir or build dir
        if any(part.startswith(('.', '_')) or part in ('build', 'dist', 'venv', 'env', 'node_modules') for part in path.parts):
            continue
            
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
            name = data.get("project", {}).get("name")
            if name:
                packages.append(name)
        except Exception:
            continue
            
    return sorted(list(set(packages)))


@app.command()
def update_readme_versions(
    packages: Optional[list[str]] = typer.Argument(None, help="List of packages to track. If not provided, reads from pyproject.toml [tool.sage-pypi-publisher] or scans directory."),
    readme_path: Path = typer.Option("README.md", "--readme", "-r", help="Path to README.md"),
    auto_discover: bool = typer.Option(True, help="Auto discover packages in current directory if config is missing"),
):
    """Update README.md with latest versions from PyPI for given packages."""
    
    if not packages:
        # 1. Try to read from pyproject.toml config
        try:
            if Path("pyproject.toml").exists():
                with open("pyproject.toml", "rb") as f:
                    data = tomllib.load(f)
                packages = data.get("tool", {}).get("sage-pypi-publisher", {}).get("tracked-packages", [])
        except Exception as e:
            console.print(f"[yellow]Could not read config from pyproject.toml: {e}[/yellow]")
    
    if not packages and auto_discover:
        # 2. Auto-discover from monorepo
        console.print("[yellow]No packages configured. Scanning for packages in current directory...[/yellow]")
        packages = find_monorepo_packages(Path("."))
        if packages:
            console.print(f"[green]Discovered packages: {', '.join(packages)}[/green]")
    
    if not packages:
        console.print("[red]No packages specified, configured, or found in directory.[/red]")
        console.print("Please provide package names, configure [tool.sage-pypi-publisher] tracked-packages, or run in a monorepo root.")
        raise typer.Exit(code=1)

    if not readme_path.exists():
        console.print(f"[red]README file not found: {readme_path}[/red]")
        raise typer.Exit(code=1)
        
    content = readme_path.read_text(encoding="utf-8")
    
    start_marker = "<!-- START_VERSION_TABLE -->"
    end_marker = "<!-- END_VERSION_TABLE -->"
    
    if start_marker not in content or end_marker not in content:
        console.print(f"[yellow]Markers not found in {readme_path}. Appending new table...[/yellow]")
        # Append to end if not found
        content += f"\n\n## Component Versions\n\n{start_marker}\n{end_marker}\n"
    
    # Fetch versions
    rows = []
    for pkg in packages:
        try:
            resp = requests.get(f"https://pypi.org/pypi/{pkg}/json", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                version = data["info"]["version"]
                rows.append(f"| [{pkg}](https://pypi.org/project/{pkg}/) | [![PyPI](https://img.shields.io/pypi/v/{pkg})](https://pypi.org/project/{pkg}/) | `{version}` |")
                console.print(f"[green]✓ Found {pkg}: {version}[/green]")
            else:
                rows.append(f"| {pkg} | Not Found | - |")
                console.print(f"[red]✗ {pkg}: Not found on PyPI[/red]")
        except Exception as e:
            rows.append(f"| {pkg} | Error | - |")
            console.print(f"[red]Error fetching {pkg}: {e}[/red]")
            
    header = "| Component | Status | Latest Version |\n|-----------|--------|----------------|\n"
    table_content = header + "\n".join(rows) + "\n"
    
    # Replace content between markers
    import re
    pattern = f"{re.escape(start_marker)}.*?{re.escape(end_marker)}"
    replacement = f"{start_marker}\n{table_content}{end_marker}"
    
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    if new_content != content:
        readme_path.write_text(new_content, encoding="utf-8")
        console.print(f"[bold green]Updated {readme_path} successfully![/bold green]")
    else:
        console.print("[yellow]No changes needed.[/yellow]")


def main():  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    main()


