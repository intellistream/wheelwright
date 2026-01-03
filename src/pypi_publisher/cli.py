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


def main():  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
