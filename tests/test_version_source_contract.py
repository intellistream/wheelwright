from __future__ import annotations

import re
import sys
from pathlib import Path


def test_version_source_contract():
    root = Path(__file__).resolve().parents[1]
    pyproject = root / "pyproject.toml"
    if sys.version_info < (3, 11):
        raise RuntimeError("Python 3.11+ is required for tomllib")

    import tomllib

    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

    project = data.get("project", {})
    assert "version" not in project
    assert "version" in project.get("dynamic", [])

    attr = (
        data.get("tool", {}).get("setuptools", {}).get("dynamic", {}).get("version", {}).get("attr")
    )
    assert attr == "pypi_publisher._version.__version__"

    version_file = root / "src" / "pypi_publisher" / "_version.py"
    init_file = root / "src" / "pypi_publisher" / "__init__.py"

    version_text = version_file.read_text(encoding="utf-8")
    assert re.search(r'^__version__\s*=\s*"[^"]+"\s*$', version_text, re.M)

    init_text = init_file.read_text(encoding="utf-8")
    patterns = [
        r"^from\s+pypi_publisher\._version\s+import\s+.*__version__",
        r"^from\s+\._version\s+import\s+.*__version__",
    ]
    assert any(re.search(pattern, init_text, re.M) for pattern in patterns)
    assert not re.search(r'^__version__\s*=\s*"[^"]+"\s*$', init_text, re.M)
