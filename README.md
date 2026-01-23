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

### Quick Start

**Interactive Mode (Recommended)** - Build and get prompted to upload:
```bash
sage-pypi-publisher build .
# After build completes, you'll be asked:
# - "是否立即上传到 PYPI?" (Upload to PyPI?)
# - "是否执行真实上传?" (Execute real upload?)
```

**One-Command Build & Upload**:
```bash
# Test on TestPyPI first (dry-run)
sage-pypi-publisher build . --upload -r testpypi

# Real upload to PyPI
sage-pypi-publisher build . --upload -r pypi --no-dry-run

# Public mode (source code)
sage-pypi-publisher build . --upload -r pypi --no-dry-run --mode public
```

### All Commands

```bash
sage-pypi-publisher --help

# Compile only (bytecode mode by default)
sage-pypi-publisher compile /path/to/pkg -o /tmp/out

# Compile in public mode (keep source)
sage-pypi-publisher compile /path/to/pkg -o /tmp/out --mode public

# Build (auto-detects pure Python vs C/C++ extensions)
sage-pypi-publisher build /path/to/pkg

# Build with upload (interactive prompts)
sage-pypi-publisher build /path/to/pkg --upload -r testpypi

# Build with auto-upload (no prompts)
sage-pypi-publisher build /path/to/pkg --upload -r pypi --no-dry-run

# Force manylinux build for C/C++ extensions
sage-pypi-publisher build /path/to/pkg --force-manylinux

# Upload an existing wheel
sage-pypi-publisher upload dist/yourpkg-0.1.0-py3-none-any.whl -r pypi --no-dry-run
```

### Build Modes

- **`--mode private`** (default): Compile to `.pyc` bytecode (保密模式 - protects source code)
- **`--mode public`**: Keep `.py` source files (公开模式 - open source)
- Aliases: `bytecode` = `private`, `source` = `public`

## Python API
```python
from pathlib import Path
from pypi_publisher.compiler import BytecodeCompiler

compiler = BytecodeCompiler(Path("/path/to/pkg"))
compiled = compiler.compile_package()
wheel = compiler.build_wheel(compiled)
compiler.upload_wheel(wheel, repository="testpypi", dry_run=True)
```

## Git Hooks

sage-pypi-publisher provides intelligent git hooks to simplify version management and PyPI publishing.

### Installation

```bash
sage-pypi-publisher install-hooks .
```

### Features

- **Auto-detection**: Detects version changes in `pyproject.toml` on push.
- **Interactive Update**: Prompts to update version if forgotten.
- **Auto-Publish**: Builds and uploads to PyPI automatically upon confirmation.
- **Smart Build**: Detects C/C++ extensions for manylinux wheels.

## Notes
- Requires `python -m build` and `twine` available.
- No backward compatibility with `sage-dev` CLI; PyPI commands have been removed from SAGE.
- Designed to be monorepo-friendly but works with any package path that contains `pyproject.toml`.
