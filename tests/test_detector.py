from __future__ import annotations

from pathlib import Path

from wheelwright.detector import detect_build_system


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_detect_pure_python_when_no_pyproject_but_plain_setup(tmp_path: Path) -> None:
    _write(tmp_path / "setup.py", "from setuptools import setup\nsetup(name='demo')\n")

    assert detect_build_system(tmp_path) == "pure-python"


def test_detect_extension_from_pyproject_requires(tmp_path: Path) -> None:
    _write(
        tmp_path / "pyproject.toml",
        """
[build-system]
requires = ["setuptools>=64", "pybind11>=2.0"]
build-backend = "setuptools.build_meta"
""".strip(),
    )

    assert detect_build_system(tmp_path) == "extension"


def test_detect_extension_from_setup_ext_modules(tmp_path: Path) -> None:
    _write(
        tmp_path / "pyproject.toml",
        """
[build-system]
requires = ["setuptools>=64"]
build-backend = "setuptools.build_meta"
""".strip(),
    )
    _write(
        tmp_path / "setup.py",
        """
from setuptools import setup, Extension
setup(name='demo', ext_modules=[Extension('mod', ['mod.c'])])
""".strip(),
    )

    assert detect_build_system(tmp_path) == "extension"
