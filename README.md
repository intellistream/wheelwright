# wheelwright

Wheelwright is a Python packaging workflow tool that compiles packages to bytecode, builds wheels, and publishes to PyPI/TestPyPI.

## Features
- Copy a package tree and compile `.py` → `.pyc` (keeps `__init__.py` and `_version.py`).
- Auto-adjust `pyproject.toml` / `MANIFEST.in` to include compiled artifacts and binary extensions.
- Build wheels with `python -m build`.
- **🚀 NEW:** Smart `--for-pypi` mode - one command for perfect PyPI publishing!
- **NEW:** Universal wheel support - one wheel works on all Python 3.x versions!
- **NEW:** Source distribution (sdist) support - users can install from source on any version
- Upload via `twine` (with `--dry-run` by default).
- Simple Typer-based CLI.

## Solving the Multi-Version Problem

**Problem:** Your package declares support for Python 3.8-3.12, but you only upload a wheel for Python 3.11. Users on other versions can't install it!

**Solution:** wheelwright now uses **Smart Mode by default** 🎯

```bash
# That's it! No extra flags needed - smart mode is automatic
wheelwright build . --upload --no-dry-run
```

**What happens automatically:**
- ✅ **Pure Python packages**: Builds universal wheel (py3-none-any) that works on **ALL** Python 3.x versions!
- ✅ **Packages with C extensions**: Builds for current Python + provides source code for others
- ✅ Always includes source distribution (sdist) as fallback
- ✅ No need to build wheels for each Python version separately!

**Why this works:**
- **Universal wheel (py3-none-any)**: One file works on Python 3.8, 3.9, 3.10, 3.11, 3.12, and future versions!
- **Source distribution**: If universal wheel doesn't work, users can compile from source
- **Zero configuration**: Works perfectly out of the box!

## Installation
```bash
pip install .
# or
pip install wheelwright
```

## CLI

### Quick Start

**🎯 Simplest Usage (Smart Mode - Default!)**
```bash
# Just build - automatically chooses best strategy!
wheelwright build .

# Build and upload to TestPyPI
wheelwright build . --upload -r testpypi

# Build and upload to PyPI (production)
wheelwright build . --upload --no-dry-run -r pypi
```

**What Smart Mode Does (Automatically):**
- 🔍 Detects if your package is pure Python or has C extensions
- 📦 Pure Python → builds universal wheel (works on ALL Python 3.x!)
- 🔧 C extensions → builds for current Python version
- 📚 Always includes source distribution (sdist)
- ✅ Perfect for packages declaring Python 3.8+ support!

**Manual Control (Advanced):**
```bash
# Disable smart mode (old behavior - current Python only)
wheelwright build . --no-for-pypi

# Force universal wheel
wheelwright build . --universal

# Force specific mode
wheelwright build . --mode public
```

### All Commands

```bash
wheelwright --help

# 🎯 Simplest: Build with smart mode (default!)
wheelwright build .

# Build and upload to PyPI
wheelwright build . --upload --no-dry-run

# Compile only (bytecode mode by default)
wheelwright compile /path/to/pkg -o /tmp/out

# Compile in public mode (keep source)
wheelwright compile /path/to/pkg -o /tmp/out --mode public

# Disable smart mode (old behavior)
wheelwright build /path/to/pkg --no-for-pypi

# Force universal wheel (manual override)
wheelwright build /path/to/pkg --universal

# Force manylinux build for C/C++ extensions
wheelwright build /path/to/pkg --force-manylinux

# Upload an existing wheel
wheelwright upload dist/yourpkg-0.1.0-py3-none-any.whl -r pypi --no-dry-run
```

### Build Modes

- **`--mode private`** (default): Compile to `.pyc` bytecode (保密模式 - protects source code)
- **`--mode public`**: Keep `.py` source files (公开模式 - open source)
- Aliases: `bytecode` = `private`, `source` = `public`

## Python API

### Basic Usage
```python
from pathlib import Path
from wheelwright.compiler import BytecodeCompiler

# Create compiler
compiler = BytecodeCompiler(Path("/path/to/pkg"), mode="private")
compiled = compiler.compile_package()

# Build wheel
wheel = compiler.build_wheel(compiled)

# Upload to TestPyPI (safe default)
compiler.upload_wheel(wheel, repository="testpypi", dry_run=True)
```

### PyPI Publishing Options

- **Smart Mode (default)**: Automatically chooses packaging strategy for PyPI.
- **`--no-for-pypi`**: Disable smart mode and use current-interpreter build behavior.
- **`--universal`**: Force `py3-none-any` wheel (pure Python only).
- **`--sdist`**: Also build source distribution (`.tar.gz`).

For C/C++ extension packages targeting multiple Python versions, use `cibuildwheel` in CI.

## Git Hooks

wheelwright provides intelligent git hooks to simplify version management and PyPI publishing.

### Hook Installation

```bash
wheelwright install-hooks .
```

### Hook Features

- **Version Guard**: Detects if the current version is already published on PyPI.
- **Auto-bump on Conflict**: Can auto-bump patch version when a duplicate release is detected.
- **Interactive Flow**: Keeps release behavior explicit and visible during push.

## Notes
- Requires `python -m build` and `twine` available.
- No backward compatibility with `sage-dev` CLI; PyPI commands have been removed from SAGE.
- Designed to be monorepo-friendly but works with any package path that contains `pyproject.toml`.
