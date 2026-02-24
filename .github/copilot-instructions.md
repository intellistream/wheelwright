# sage-pypi-publisher Copilot Instructions

## Scope
- Python toolkit for bytecode compile, wheel build, and PyPI/TestPyPI publishing.
- Core package: `src/pypi_publisher/` with Typer CLI.

## Critical rules
- Keep strong typing, Google-style docstrings, and clear exception hierarchy.
- Preserve compile rules: keep `__init__.py` and `_version.py` as source; compile other Python files as configured.
- Use Rich for user-facing output; keep messages concise and consistent.
- No fallback logic; use explicit exceptions (`CompilationError`, `BuildError`, `UploadError`).
- Do not create new virtual environments in repo workflows.

## Workflow
1. Update compiler/CLI logic minimally and coherently.
2. Add tests for success and failure paths.
3. Run lint/type/tests before handoff.

## Key paths
- `src/pypi_publisher/cli.py`, `compiler.py`, `exceptions.py`, `pyproject.toml`.
