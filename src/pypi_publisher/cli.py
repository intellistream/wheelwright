"""Command line interface for sage-pypi-publisher."""
from __future__ import annotations

from pathlib import Path

import requests
import typer
from rich.console import Console

from pypi_publisher._version import __version__
from pypi_publisher.compiler import BytecodeCompiler
from pypi_publisher.detector import detect_build_system
from pypi_publisher.manylinux_builder import ManylinuxBuilder

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

# Known SAGE packages to always include in version checks
KNOWN_SAGE_PACKAGES = [
    "isage-pypi-publisher", "isage-kernel", "isage-middleware", "isage-neuromem",
    "isage", "isage-llm-gateway", "isage-libs", "isage-llm-core", "isage-common",
    "isage-data", "isage-vdb", "isage-tsdb", "isage-refiner", "isage-flow",
    "isage-benchmark", "sage-github-manager", "isage-edge", "isage-tools",
    "isage-studio", "isage-apps", "isage-cli", "isage-platform", "intellistream",
    "pysame"
]

console = Console()
app = typer.Typer(name="sage-pypi-publisher", add_completion=False, no_args_is_help=True)


@app.command()
def compile(
    package_path: Path = typer.Argument(..., help="Path to the package directory containing pyproject.toml"),
    output_dir: Path | None = typer.Option(None, "--output", "-o", help="Output directory for compiled package"),
    mode: str = typer.Option(
        "private",
        "--mode",
        "-m",
        help="Build mode: 'private'/'bytecode' (保密) or 'public'/'source' (公开)",
    ),
):
    """
    Compile a package to bytecode (py -> pyc) or prepare for source distribution.

    Modes:

    - private/bytecode: Compile to .pyc (保密模式 - 保护源码)

    - public/source: Keep .py source files (公开模式 - 开源发布)
    """
    compiler = BytecodeCompiler(package_path, mode=mode)  # type: ignore
    compiled = compiler.compile_package(output_dir)
    console.print(f"[bold green]✓ 编译完成: {compiled}[/bold green]")


@app.command()
def build(
    package_path: Path = typer.Argument(..., help="Path to the package directory"),
    output_dir: Path | None = typer.Option(None, "--output", "-o", help="Output directory"),
    upload: bool = typer.Option(False, "--upload", "-u", help="Upload after build"),
    repository: str = typer.Option("pypi", "--repository", "-r", help="pypi or testpypi"),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Skip actual upload when true"),
    force_manylinux: bool = typer.Option(False, "--force-manylinux", help="Force manylinux build"),
    force_bytecode: bool = typer.Option(False, "--force-bytecode", help="Force bytecode compilation"),
    platform_tag: str = typer.Option("manylinux_2_34_x86_64", "--platform", "-p", help="Manylinux platform tag (for extension packages)"),
    mode: str = typer.Option(
        "private",
        "--mode",
        "-m",
        help="Build mode: 'private'/'bytecode' (compile to .pyc) or 'public'/'source' (keep .py source)",
    ),
):
    """
    Smart build: auto-detects package type and builds appropriately.

    - C/C++ extension packages → manylinux wheel
    - Pure Python packages → bytecode compilation (default) or source

    Use --force-manylinux or --force-bytecode to override auto-detection.
    Use --mode to choose between private (bytecode) or public (source) builds.
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
        # Build wheel for pure Python (with mode support)
        mode_name = "保密模式 (字节码)" if mode in ("private", "bytecode") else "公开模式 (源码)"
        console.print(f"🔧 Building as pure Python package - {mode_name}...")
        compiler = BytecodeCompiler(package_path, mode=mode)  # type: ignore
        compiled = compiler.compile_package(output_dir)
        wheel_path = compiler.build_wheel(compiled)
        console.print(f"[bold green]✓ 构建成功: {wheel_path}[/bold green]")

    if upload:
        compiler = BytecodeCompiler(package_path, mode=mode)  # type: ignore
        compiler.upload_wheel(wheel_path, repository=repository, dry_run=dry_run)


@app.command("build-manylinux")
def build_manylinux(
    package_path: Path = typer.Argument(..., help="Path to the package directory"),
    output_dir: Path | None = typer.Option(None, "--output", "-o", help="Output directory (default: ./wheelhouse)"),
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


def print_version(value: bool):
    if value:
        console.print(f"sage-pypi-publisher {__version__}")
        raise typer.Exit()

@app.callback()
def main_callback(
    version: bool | None = typer.Option(
        None, "--version", callback=print_version, is_eager=True, help="Show version and exit"
    )
):
    pass




@app.command()
def install_hooks(
    package_path: Path = typer.Argument(".", help="Path to the package directory"),
):
    """Install sage-pypi-publisher git hooks (pre-commit, pre-push) into your repository."""
    from pypi_publisher.hooks import install_git_hooks

    console.print("[bold]Installing git hooks...[/bold]")
    success = install_git_hooks(package_path)

    if success:
        console.print("\n[green]✓ Ready to use![/green]")
        console.print("\n[bold]Hooks installed:[/bold]")
        console.print("  • [cyan]pre-commit[/cyan]: Runs code quality checks (ruff, mypy)")
        console.print("  • [cyan]pre-push[/cyan]:   Auto-detects version updates & uploads to PyPI")



@app.command()
def uninstall_hooks(
    package_path: Path = typer.Argument(".", help="Path to the package directory"),
):
    """Uninstall sage-pypi-publisher git hooks."""
    from pypi_publisher.hooks import uninstall_git_hooks

    console.print("[bold]Uninstalling git hooks...[/bold]")
    uninstall_git_hooks(package_path)


def find_monorepo_packages(root: Path) -> dict[str, str]:
    """Find all packages and their local versions in the monorepo by scanning pyproject.toml files."""
    packages = {}

    console.print(f"[dim]Scanning {root} for python packages...[/dim]")

    for path in root.rglob("pyproject.toml"):
        # Skip if in hidden dir or build dir
        if any(part.startswith(('.', '_')) or part in ('build', 'dist', 'venv', 'env', 'node_modules') for part in path.parts):
            continue

        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
            project = data.get("project", {})
            name = project.get("name")
            version = project.get("version", "0.0.0")
            if name:
                packages[name] = version
        except Exception:
            continue

    return packages


@app.command()
def list_versions(
    packages: list[str] | None = typer.Argument(None, help="List of packages to check. If not provided, scans directory and uses known SAGE packages."),
    auto_discover: bool = typer.Option(True, help="Auto discover packages in current directory if config is missing"),
    show_all: bool = typer.Option(False, "--show-all", "-a", help="Show all known packages even if not found locally"),
):
    """
    List local packages and compare with PyPI versions.

    Scans the current directory (recursively) for `pyproject.toml` files,
    finds the package name and local version, checks PyPI, and displays a comparison table.

    Includes known SAGE ecosystem packages by default.
    """
    from packaging.version import parse as parse_version
    from rich.table import Table

    local_packages = {}
    target_packages = set()

    # 1. Determine local packages (always scan to get versions if available)
    if auto_discover:
        local_packages = find_monorepo_packages(Path("."))

    # 2. Determine target list of packages to display
    if packages:
        # User specified packages explicitly
        target_packages = set(packages)
    else:
        # Default: Local packages + Known SAGE packages
        target_packages = set(local_packages.keys()) | set(KNOWN_SAGE_PACKAGES)

    if not target_packages:
        console.print("[red]No packages found or specified.[/red]")
        raise typer.Exit(code=1)

    table = Table(title="📦 Package Version Status")
    table.add_column("Package", style="cyan", no_wrap=True)
    table.add_column("Local Version", style="magenta")
    table.add_column("PyPI Version", style="green")
    table.add_column("Status", style="bold")

    with console.status("[bold green]Fetching PyPI info..."):
        for pkg_name in sorted(target_packages):
            local_ver = local_packages.get(pkg_name)

            # If not local and not showing all (implied by default behavior logic check)
            # Actually, user requested "put our projects in", so we probably want to show them all.
            # But let's differentiate visually.

            pypi_ver = _fetch_pypi_version(pkg_name)

            if not local_ver and not pypi_ver:
                # Neither local nor remote - skip if it came from the known list?
                # No, if it's in known list but not on pypi, maybe we should show "Not in PyPI"
                # But to avoid clutter, maybe we hide it if user didn't ask for it explicitly?
                # User asked to "put projects in", so let's show them.
                pass

            status = ""
            status_style = ""

            display_local = local_ver if local_ver else "[dim]Not Local[/dim]"

            if not pypi_ver:
                pypi_ver = "[dim]Not Found[/dim]"
                status = "Unpublished"
                status_style = "dim"
                if local_ver:
                    status = "New Package"
                    status_style = "blue"
            else:
                if local_ver:
                    try:
                        v_local = parse_version(local_ver)
                        v_pypi = parse_version(pypi_ver)

                        if v_local > v_pypi:
                            status = "🚀 Ready to Publish"
                            status_style = "green"
                        elif v_local < v_pypi:
                            status = "⚠️ Local behind PyPI"
                            status_style = "yellow"
                        else:
                            status = "✓ Up to date"
                            status_style = "dim"

                    except Exception:
                        status = "Unknown"
                else:
                    status = "Remote Only"
                    status_style = "cyan"

            table.add_row(
                pkg_name,
                display_local,
                pypi_ver,
                f"[{status_style}]{status}[/{status_style}]"
            )

    console.print(table)


def _fetch_pypi_version(package_name: str) -> str | None:
    """Fetch latest version from PyPI JSON API."""
    try:
        resp = requests.get(f"https://pypi.org/pypi/{package_name}/json", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data["info"]["version"]
    except Exception:
        pass
    return None



def main():  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    main()


