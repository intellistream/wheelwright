"""Detect package build system and type."""
from __future__ import annotations

from pathlib import Path

import tomli


def detect_build_system(package_path: Path) -> str:
    """
    Detect the build system used by a package.

    Returns:
        'extension' for C/C++ extension packages (scikit-build, setuptools with ext_modules)
        'pure-python' for pure Python packages
    """
    pyproject_file = package_path / "pyproject.toml"

    if not pyproject_file.exists():
        # No pyproject.toml, assume pure Python with setup.py
        setup_py = package_path / "setup.py"
        if setup_py.exists():
            content = setup_py.read_text(encoding="utf-8")
            if "ext_modules" in content or "Extension" in content:
                return "extension"
        return "pure-python"

    try:
        with open(pyproject_file, "rb") as f:
            data = tomli.load(f)
    except Exception:
        return "pure-python"

    # Check build-system.requires
    build_system = data.get("build-system", {})
    requires = build_system.get("requires", [])

    # Check for C/C++ extension build systems

    for req in requires:
        req_lower = req.lower()
        if any(marker in req_lower for marker in ["scikit-build", "pybind11", "cython", "meson-python"]):
            return "extension"

    # If using setuptools, check for CMakeLists.txt or other signs
    if any("setuptools" in req.lower() for req in requires):
        if (package_path / "CMakeLists.txt").exists():
            return "extension"
        if (package_path / "setup.py").exists():
            setup_content = (package_path / "setup.py").read_text(encoding="utf-8")
            if "ext_modules" in setup_content or "Extension" in setup_content:
                return "extension"

    return "pure-python"


try:
    import tomli
except ImportError:
    # Fallback for Python 3.11+
    import tomllib as tomli  # type: ignore
