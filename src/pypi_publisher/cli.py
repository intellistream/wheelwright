"""Command line interface for sage-pypi-publisher."""

from __future__ import annotations

import re
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
    "isage-pypi-publisher",
    "isage-kernel",
    "isage-middleware",
    "isage-neuromem",
    "isage",
    "isage-llm-gateway",
    "isage-libs",
    "isage-llm-core",
    "isage-common",
    "isage-data",
    "isage-vdb",
    "isage-tsdb",
    "isage-refiner",
    "isage-flow",
    "isage-benchmark",
    "sage-github-manager",
    "isage-edge",
    "isage-tools",
    "isage-studio",
    "isage-apps",
    "isage-cli",
    "isage-platform",
    "intellistream",
    "pysame",
]

console = Console()
app = typer.Typer(name="sage-pypi-publisher", add_completion=False, no_args_is_help=True)


@app.command()
def compile(
    package_path: Path = typer.Argument(
        ..., help="Path to the package directory containing pyproject.toml"
    ),
    output_dir: Path | None = typer.Option(
        None, "--output", "-o", help="Output directory for compiled package"
    ),
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
    dry_run: bool = typer.Option(
        True, "--dry-run/--no-dry-run", help="Skip actual upload when true"
    ),
    force_manylinux: bool = typer.Option(False, "--force-manylinux", help="Force manylinux build"),
    force_bytecode: bool = typer.Option(
        False, "--force-bytecode", help="Force bytecode compilation"
    ),
    platform_tag: str = typer.Option(
        "manylinux_2_34_x86_64",
        "--platform",
        "-p",
        help="Manylinux platform tag (for extension packages)",
    ),
    mode: str = typer.Option(
        "private",
        "--mode",
        "-m",
        help="Build mode: 'private'/'bytecode' (compile to .pyc) or 'public'/'source' (keep .py source)",
    ),
    auto_bump: str | None = typer.Option(
        None, "--auto-bump", help="Auto bump version: patch/minor/major"
    ),
    for_pypi: bool = typer.Option(
        True,  # Default to True - smart mode by default!
        "--for-pypi/--no-for-pypi",
        help="Smart PyPI mode (default): auto-detect best strategy. Use --no-for-pypi to disable.",
    ),
    universal: bool = typer.Option(
        False, "--universal", help="Force universal wheel (py3-none-any) - overrides smart mode"
    ),
    sdist: bool = typer.Option(False, "--sdist", help="Also build source distribution (.tar.gz)"),
    auto_push: bool = typer.Option(
        False,
        "--auto-push/--no-auto-push",
        help="Auto-push to GitHub after upload (default: False)",
    ),
):
    """
    Smart build: auto-detects package type and builds appropriately.

    **🎯 Default Behavior (Smart Mode):**
    - Automatically enabled! No extra flags needed
    - Pure Python packages → universal wheel (py3-none-any) + sdist
    - C/C++ extension packages → current Python wheel + sdist
    - Perfect for packages declaring Python 3.8+ support

    **Simplest Usage (Recommended):**
    ```bash
    # Just build - smart mode is automatic!
    sage-pypi-publisher build .

    # Build and upload to PyPI
    sage-pypi-publisher build . --upload --no-dry-run

    # Test on TestPyPI first
    sage-pypi-publisher build . --upload -r testpypi
    ```

    **Why this solves the multi-version problem:**
    - Universal wheel: One file works on ALL Python 3.x (3.8, 3.9, 3.10, 3.11, 3.12+)
    - Source dist: Users can compile from source if needed
    - No need to build separate wheels for each Python version!

    **Manual Override Options:**
    - --no-for-pypi: Disable smart mode, build for current Python only
    - --universal: Force universal wheel (overrides smart detection)
    - --sdist: Add source distribution (in addition to smart mode)
    - --force-manylinux: Force manylinux build for C extensions

    Examples:
        # Default: Smart mode (automatically chooses best strategy)
        sage-pypi-publisher build .

        # Upload to TestPyPI (smart mode still active)
        sage-pypi-publisher build . --upload -r testpypi

        # Real PyPI upload
        sage-pypi-publisher build . --upload --no-dry-run -r pypi

        # Disable smart mode (old behavior)
        sage-pypi-publisher build . --no-for-pypi
    """
    # Handle version auto-bump if requested
    if auto_bump:
        _bump_version(package_path, auto_bump)

    build_system = detect_build_system(package_path)

    if force_manylinux:
        build_system = "extension"
    elif force_bytecode:
        build_system = "pure-python"

    console.print(f"🔍 Detected build system: [cyan]{build_system}[/cyan]")

    # Track all built artifacts
    built_artifacts: list[Path] = []

    if build_system == "extension":
        # Build manylinux wheel for C/C++ extensions
        console.print("🔧 Building as C/C++ extension package with manylinux tags...")
        builder = ManylinuxBuilder(package_path)
        wheel_path = builder.build_manylinux_wheel(
            output_dir=output_dir,
            platform_tag=platform_tag,
        )
        built_artifacts.append(wheel_path)
        console.print(f"[bold green]✓ 构建成功: {wheel_path.name}[/bold green]")
    else:
        # Build wheel for pure Python (with mode support)
        mode_name = "保密模式 (字节码)" if mode in ("private", "bytecode") else "公开模式 (源码)"
        console.print(f"🔧 Building as pure Python package - {mode_name}...")

        # Initialize compiler
        compiler = BytecodeCompiler(package_path, mode=mode)  # type: ignore
        compiled = compiler.compile_package(output_dir)

        # Check if user explicitly wants manual control
        manual_mode = universal or (sdist and not for_pypi)

        if for_pypi and not manual_mode:
            # Smart PyPI mode (DEFAULT): auto-detect best strategy
            console.print("\n🎯 智能模式（默认）：自动选择最佳发布策略...", style="cyan bold")

            if build_system == "pure-python" or mode == "public":
                # Pure Python: universal wheel + sdist
                console.print("  ✓ 检测到纯Python包")
                console.print("  📦 策略：通用wheel (py3-none-any) + 源码分发", style="cyan")
                console.print("  💡 这样所有Python 3.x版本都能安装！\n")

                wheel_path = compiler.build_universal_wheel(compiled)
                built_artifacts.append(wheel_path)

                sdist_path = compiler.build_sdist(compiled)
                built_artifacts.append(sdist_path)
            else:
                # Has extensions: current Python wheel + sdist
                console.print("  ✓ 检测到C/C++扩展包")
                console.print("  📦 策略：当前Python版本wheel + 源码分发", style="cyan")
                console.print("  💡 用户可以从源码编译安装到其他Python版本\n")

                wheel_path = compiler.build_wheel(compiled)
                built_artifacts.append(wheel_path)

                sdist_path = compiler.build_sdist(compiled)
                built_artifacts.append(sdist_path)
        elif universal:
            # Manual: Build universal wheel only
            console.print("\n🌍 Building universal wheel (py3-none-any)...")
            wheel_path = compiler.build_universal_wheel(compiled)
            built_artifacts.append(wheel_path)
        else:
            # Standard build for current Python version
            wheel_path = compiler.build_wheel(compiled)
            built_artifacts.append(wheel_path)
            console.print(f"[bold green]✓ 构建成功: {wheel_path}[/bold green]")

        # Build sdist if requested (and not already built by for_pypi)
        if sdist and not for_pypi:
            console.print("\n📚 Building source distribution...")
            sdist_path = compiler.build_sdist(compiled)
            built_artifacts.append(sdist_path)

    # Summary of built artifacts
    if len(built_artifacts) > 1:
        console.print(
            f"\n✅ [bold green]Successfully built {len(built_artifacts)} artifacts:[/bold green]"
        )
        for artifact in built_artifacts:
            console.print(f"   📦 {artifact.name}")

    # Handle upload: auto-upload or prompt user
    if upload:
        console.print(f"\n🚀 准备上传到 {repository.upper()}...")
        compiler = BytecodeCompiler(package_path, mode=mode)  # type: ignore
        for artifact in built_artifacts:
            console.print(f"\n  📤 Uploading: {artifact.name}")
            compiler.upload_wheel(
                artifact, repository=repository, dry_run=dry_run, auto_push=auto_push
            )
    else:
        # Ask user if they want to upload
        console.print("\n📦 Built artifacts:")
        for artifact in built_artifacts:
            console.print(f"   • [cyan]{artifact}[/cyan]")

        if len(built_artifacts) > 0:
            should_upload = typer.confirm(f"\n是否立即上传到 {repository.upper()}?", default=False)

            if should_upload:
                # Ask about dry-run mode if not explicitly set
                if dry_run:
                    real_upload = typer.confirm(
                        "⚠️  当前为 dry-run 模式 (不会真正上传)。是否执行真实上传?", default=False
                    )
                    if real_upload:
                        dry_run = False

                console.print(f"\n🚀 准备上传到 {repository.upper()}...")
                compiler = BytecodeCompiler(package_path, mode=mode)  # type: ignore
                for artifact in built_artifacts:
                    console.print(f"\n  📤 Uploading: {artifact.name}")
                    compiler.upload_wheel(
                        artifact, repository=repository, dry_run=dry_run, auto_push=False
                    )
            else:
                console.print("\n💡 跳过上传。如需上传，可以运行:")
                console.print(
                    f"   [cyan]sage-pypi-publisher upload <artifact> -r {repository} --no-dry-run[/cyan]"
                )


@app.command("build-manylinux")
def build_manylinux(
    package_path: Path = typer.Argument(..., help="Path to the package directory"),
    output_dir: Path | None = typer.Option(
        None, "--output", "-o", help="Output directory (default: ./wheelhouse)"
    ),
    platform_tag: str = typer.Option(
        "manylinux_2_34_x86_64", "--platform", "-p", help="Manylinux platform tag"
    ),
    upload: bool = typer.Option(False, "--upload", "-u", help="Upload after build"),
    repository: str = typer.Option("pypi", "--repository", "-r", help="pypi or testpypi"),
    dry_run: bool = typer.Option(
        True, "--dry-run/--no-dry-run", help="Skip actual upload when true"
    ),
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

    # Handle upload: auto-upload or prompt user
    if upload:
        console.print(f"\n🚀 准备上传到 {repository.upper()}...")
        from pypi_publisher.compiler import BytecodeCompiler

        compiler = BytecodeCompiler(package_path)
        compiler.upload_wheel(wheel_path, repository=repository, dry_run=dry_run)
    else:
        # Ask user if they want to upload
        console.print(f"\n📦 Wheel 文件: [cyan]{wheel_path}[/cyan]")
        should_upload = typer.confirm(f"是否立即上传到 {repository.upper()}?", default=False)

        if should_upload:
            # Ask about dry-run mode if not explicitly set
            if dry_run:
                real_upload = typer.confirm(
                    "⚠️  当前为 dry-run 模式 (不会真正上传)。是否执行真实上传?", default=False
                )
                if real_upload:
                    dry_run = False

            console.print(f"\n🚀 准备上传到 {repository.upper()}...")
            from pypi_publisher.compiler import BytecodeCompiler

            compiler = BytecodeCompiler(package_path)
            compiler.upload_wheel(wheel_path, repository=repository, dry_run=dry_run)
        else:
            console.print("\n💡 跳过上传。如需上传，可以运行:")
            console.print(
                f"   [cyan]sage-pypi-publisher upload {wheel_path} -r {repository} --no-dry-run[/cyan]"
            )


@app.command()
def upload(
    wheel_path: Path = typer.Argument(..., help="Wheel file to upload"),
    repository: str = typer.Option("pypi", "--repository", "-r", help="pypi or testpypi"),
    dry_run: bool = typer.Option(
        True, "--dry-run/--no-dry-run", help="Skip actual upload when true"
    ),
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
    ),
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
        if any(
            part.startswith((".", "_")) or part in ("build", "dist", "venv", "env", "node_modules")
            for part in path.parts
        ):
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
    packages: list[str] | None = typer.Argument(
        None,
        help="List of packages to check. If not provided, scans directory and uses known SAGE packages.",
    ),
    auto_discover: bool = typer.Option(
        True, help="Auto discover packages in current directory if config is missing"
    ),
    show_all: bool = typer.Option(
        False, "--show-all", "-a", help="Show all known packages even if not found locally"
    ),
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
                pkg_name, display_local, pypi_ver, f"[{status_style}]{status}[/{status_style}]"
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


def _bump_version(package_path: Path, bump_type: str) -> str:
    """Bump version in pyproject.toml.

    Supports 3-part (major.minor.patch) or 4-part (major.minor.micro.patch) version numbers.

    Args:
        package_path: Path to package directory containing pyproject.toml
        bump_type: 'patch', 'minor', or 'major'

    Returns:
        New version string
    """
    pyproject_path = package_path / "pyproject.toml"
    if not pyproject_path.exists():
        console.print(f"[red]❌ pyproject.toml not found in {package_path}[/red]")
        raise typer.Exit(code=1)

    # Read current version
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    current_version_str = data.get("project", {}).get("version", "0.0.0")

    # Parse version parts manually to support 4-part versions (major.minor.micro.patch)
    parts = current_version_str.split(".")
    version_parts = [int(p) for p in parts]

    # Ensure at least 3 parts
    while len(version_parts) < 3:
        version_parts.append(0)

    # Bump version based on type
    if bump_type == "patch":
        # For 4-part versions: increment last part (0.1.8.6 → 0.1.8.7)
        # For 3-part versions: increment last part (0.1.8 → 0.1.9)
        if len(version_parts) >= 4:
            version_parts[-1] += 1
        elif len(version_parts) == 3:
            version_parts.append(1)  # Add 4th part
        else:
            version_parts[-1] += 1
    elif bump_type == "minor":
        # Increment minor, reset micro and patch (0.1.8.6 → 0.1.9.0)
        version_parts[1] += 1
        for i in range(2, len(version_parts)):
            version_parts[i] = 0
    elif bump_type == "major":
        # Increment major, reset all others (0.1.8.6 → 1.0.0.0)
        version_parts[0] += 1
        for i in range(1, len(version_parts)):
            version_parts[i] = 0
    else:
        console.print(f"[red]❌ Invalid bump type: {bump_type}. Use patch/minor/major[/red]")
        raise typer.Exit(code=1)

    new_version_str = ".".join(str(p) for p in version_parts)

    # Update pyproject.toml
    with open(pyproject_path, encoding="utf-8") as f:
        content = f.read()

    # Replace version using regex (handle both quoted styles)
    version_pattern = rf'(version\s*=\s*["\'])({re.escape(current_version_str)})(["\'])'
    new_content = re.sub(version_pattern, rf"\g<1>{new_version_str}\g<3>", content)

    if new_content == content:
        console.print("[yellow]⚠️  Version pattern not found in pyproject.toml[/yellow]")
        raise typer.Exit(code=1)

    with open(pyproject_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    console.print(
        f"[bold green]✓ Version bumped: {current_version_str} → {new_version_str}[/bold green]"
    )
    return new_version_str


@app.command()
def publish(
    package_path: Path = typer.Argument(..., help="Path to the package directory"),
    auto_bump: str | None = typer.Option(
        None, "--auto-bump", help="Auto bump version: patch/minor/major"
    ),
    repository: str = typer.Option("pypi", "--repository", "-r", help="pypi or testpypi"),
    dry_run: bool = typer.Option(
        True, "--dry-run/--no-dry-run", help="Skip actual upload when true"
    ),
    mode: str = typer.Option(
        "private",
        "--mode",
        "-m",
        help="Build mode: 'private'/'bytecode' (compile to .pyc) or 'public'/'source' (keep .py source)",
    ),
    force_manylinux: bool = typer.Option(False, "--force-manylinux", help="Force manylinux build"),
    platform_tag: str = typer.Option(
        "manylinux_2_34_x86_64", "--platform", "-p", help="Manylinux platform tag"
    ),
):
    """
    🚀 One-command publish: bump version → build → upload to PyPI.

    This command combines version bumping, building, and uploading into a single operation.
    Perfect for quick releases to PyPI.

    Examples:
        # Bump patch version and publish to PyPI (dry-run)
        sage-pypi-publisher publish . --auto-bump patch

        # Real publish to PyPI
        sage-pypi-publisher publish . --auto-bump patch --no-dry-run

        # Publish to TestPyPI for testing
        sage-pypi-publisher publish . --auto-bump minor -r testpypi --no-dry-run

        # Public source release (no bytecode compilation)
        sage-pypi-publisher publish . --auto-bump patch --mode public --no-dry-run
    """
    console.print("[bold cyan]🚀 Starting publish workflow...[/bold cyan]\n")

    # Step 1: Bump version if requested
    if auto_bump:
        console.print(f"[bold]Step 1/3:[/bold] 📝 Bumping version ({auto_bump})...")
        new_version = _bump_version(package_path, auto_bump)
    else:
        console.print("[bold]Step 1/3:[/bold] ⏭️  Skipping version bump (no --auto-bump)...")
        # Get current version for display
        pyproject_path = package_path / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        new_version = data.get("project", {}).get("version", "unknown")

    console.print(f"   Version: [cyan]{new_version}[/cyan]\n")

    # Step 2: Build package
    console.print("[bold]Step 2/3:[/bold] 🔧 Building package...")
    build_system = detect_build_system(package_path)

    if force_manylinux:
        build_system = "extension"

    console.print(f"   Build type: [cyan]{build_system}[/cyan]")

    if build_system == "extension":
        builder = ManylinuxBuilder(package_path)
        wheel_path = builder.build_manylinux_wheel(
            output_dir=None,
            platform_tag=platform_tag,
        )
    else:
        mode_name = "保密模式 (字节码)" if mode in ("private", "bytecode") else "公开模式 (源码)"
        console.print(f"   Mode: [cyan]{mode_name}[/cyan]")
        compiler = BytecodeCompiler(package_path, mode=mode)  # type: ignore
        compiled = compiler.compile_package(None)
        wheel_path = compiler.build_wheel(compiled)

    console.print(f"   [green]✓ Built: {wheel_path.name}[/green]\n")

    # Step 3: Upload to PyPI
    console.print(f"[bold]Step 3/3:[/bold] 📤 Uploading to {repository.upper()}...")

    if dry_run:
        console.print("   [yellow]⚠️  DRY RUN mode - not actually uploading[/yellow]")
        console.print("   [dim]To really upload, use: --no-dry-run[/dim]\n")

    compiler = BytecodeCompiler(package_path, mode=mode)  # type: ignore
    compiler.upload_wheel(wheel_path, repository=repository, dry_run=dry_run)

    # Summary
    console.print("\n" + "=" * 60)
    if dry_run:
        console.print("[bold yellow]📋 DRY RUN 完成[/bold yellow]")
        console.print(f"\n[dim]要真正发布到 {repository.upper()}，请运行:[/dim]")
        bump_flag = f" --auto-bump {auto_bump}" if auto_bump else ""
        console.print(
            f"  [cyan]sage-pypi-publisher publish {package_path}{bump_flag} -r {repository} --no-dry-run[/cyan]"
        )
    else:
        console.print("[bold green]🎉 发布成功！[/bold green]")
        console.print(f"\n📦 Package: [cyan]{wheel_path.name}[/cyan]")
        console.print(f"🔖 Version: [cyan]{new_version}[/cyan]")
        console.print(f"🌐 Repository: [cyan]{repository.upper()}[/cyan]")
    console.print("=" * 60)


def main():  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
