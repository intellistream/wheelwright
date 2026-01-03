"""Command line interface for sage-pypi-publisher."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from pypi_publisher.compiler import BytecodeCompiler
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
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory for compiled package"),
    upload: bool = typer.Option(False, "--upload", "-u", help="Upload after build"),
    repository: str = typer.Option("pypi", "--repository", "-r", help="pypi or testpypi"),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Skip actual upload when true"),
):
    """Compile, build wheel, optionally upload."""
    compiler = BytecodeCompiler(package_path)
    compiled = compiler.compile_package(output_dir)
    wheel_path = compiler.build_wheel(compiled)
    console.print(f"[bold green]✓ 构建成功: {wheel_path}[/bold green]")
    if upload:
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
