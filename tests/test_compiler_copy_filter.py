from __future__ import annotations

import os
from pathlib import Path

from pypi_publisher.compiler import BytecodeCompiler


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _create_minimal_project(root: Path) -> None:
    _write(
        root / "pyproject.toml",
        """
[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "demo-pkg"
version = "0.0.1"
""".strip(),
    )
    _write(root / "setup.py", "from setuptools import setup\nsetup(name='demo-pkg')\n")
    _write(root / "src" / "demo_pkg" / "__init__.py", "__all__ = []\n")


def test_compile_package_ignores_sage_runtime_artifacts(tmp_path: Path) -> None:
    _create_minimal_project(tmp_path)

    runtime_dir = tmp_path / ".sage" / "temp" / "ray" / "session_x" / "sockets"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    os.mkfifo(runtime_dir / "raylet")

    out_dir = tmp_path.parent / f"{tmp_path.name}_out"
    compiler = BytecodeCompiler(tmp_path, mode="public")
    compiled = compiler.compile_package(out_dir)

    assert compiled.exists()
    assert not (compiled / ".sage").exists()


def test_copytree_ignore_skips_special_files(tmp_path: Path) -> None:
    _create_minimal_project(tmp_path)
    fifo_path = tmp_path / "runtime_socket_like"
    os.mkfifo(fifo_path)

    compiler = BytecodeCompiler(tmp_path, mode="public")
    ignored = compiler._copytree_ignore(str(tmp_path), ["runtime_socket_like", "src"])

    assert "runtime_socket_like" in ignored
    assert "src" not in ignored
