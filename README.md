# sage-pypi-publisher

A tiny toolkit to compile Python packages to bytecode, build wheels, and publish to PyPI/TestPyPI. Extracted from SAGE's internal `sage-dev` tooling and made standalone.

## Features
- Copy a package tree and compile `.py` → `.pyc` (keeps `__init__.py` and `_version.py`).
- Auto-adjust `pyproject.toml` / `MANIFEST.in` to include compiled artifacts and binary extensions.
- Build wheels with `python -m build`.
- Upload via `twine` (with `--dry-run` by default).
- Simple Typer-based CLI.

## Installation
```bash
pip install .
# or
pip install sage-pypi-publisher
```

## CLI
```bash
sage-pypi-publisher --help

# Compile only
sage-pypi-publisher compile /path/to/pkg -o /tmp/out

# Compile + build
sage-pypi-publisher build /path/to/pkg -o /tmp/out

# Compile + build + upload to TestPyPI
sage-pypi-publisher build /path/to/pkg -o /tmp/out -u -r testpypi --no-dry-run

# Upload an existing wheel
sage-pypi-publisher upload dist/yourpkg-0.1.0-py3-none-any.whl -r pypi --no-dry-run
```

## Python API
```python
from pathlib import Path
from pypi_publisher.compiler import BytecodeCompiler

compiler = BytecodeCompiler(Path("/path/to/pkg"))
compiled = compiler.compile_package()
wheel = compiler.build_wheel(compiled)
compiler.upload_wheel(wheel, repository="testpypi", dry_run=True)
```

## Notes
- Requires `python -m build` and `twine` available.
- No backward compatibility with `sage-dev` CLI; PyPI commands have been removed from SAGE.
- Designed to be monorepo-friendly but works with any package path that contains `pyproject.toml`.
