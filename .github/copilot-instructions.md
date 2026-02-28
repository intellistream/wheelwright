# GitHub Copilot Instructions for sage-pypi-publisher

## Project Overview
`sage-pypi-publisher` is a Python bytecode compiler and PyPI publishing toolkit designed for monorepo projects. It compiles Python packages to bytecode (`.py` → `.pyc`), builds wheels, and publishes to PyPI/TestPyPI.

**Key Features:**
- Compile Python packages to bytecode while preserving `__init__.py` and `_version.py`
- Auto-adjust `pyproject.toml` and `MANIFEST.in` for compiled artifacts
- Build wheels using `python -m build`
- Upload via `twine` with dry-run support
- Typer-based CLI with rich console output
- Monorepo-friendly design

## Technology Stack
- **Language**: Python 3.10+
- **CLI Framework**: Typer 0.9.0+
- **UI**: Rich 13.0.0+ (console output, progress bars)
- **Build Tools**: build 1.0.0+, twine 4.0.0+
- **Dev Tools**: pytest, ruff, mypy
- **Package Manager**: pip/setuptools

## Project Structure
```
sage-pypi-publisher/
├── src/
│   └── pypi_publisher/
│       ├── __init__.py       # Package exports
│       ├── _version.py       # Version info
│       ├── cli.py            # Typer CLI commands
│       ├── compiler.py       # Core BytecodeCompiler class
│       └── exceptions.py     # Custom exceptions
├── pyproject.toml            # Project config, dependencies, metadata
├── README.md                 # Usage documentation
└── LICENSE                   # MIT License
```

## Coding Standards

### Python Style
- **Type Hints**: Required for all functions (enforced by mypy)
- **Line Length**: 100 characters (ruff configured)
- **Imports**: Sorted and formatted (ruff I rule)
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Future Imports**: Use `from __future__ import annotations` for type hints
- **String Literals**: Use double quotes by default

### Code Quality
- **Linting**: Use ruff for linting and formatting
- **Type Checking**: All functions must have type annotations
- **Error Handling**: Use custom exceptions from `exceptions.py`
- **Console Output**: Use Rich console with Chinese-friendly messages
  - Success: `[bold green]✓ message[/bold green]`
  - Info: `style="cyan"`
  - Warning: `style="yellow"`
  - Error: `style="red"`

### Documentation
- **Docstrings**: Required for all public classes and methods
- **Format**: Google-style docstrings
- **Comments**: Use Chinese for user-facing messages, English for code comments

## Architecture Patterns

### BytecodeCompiler Class
The core class that handles:
1. **Package Compilation**: Copy package tree, compile `.py` to `.pyc`
2. **Build Process**: Generate wheels from compiled packages
3. **Upload**: Publish to PyPI/TestPyPI via twine

**Key Methods:**
- `compile_package(output_dir)`: Main compilation entry point
- `build_wheel(compiled_path)`: Build wheel from compiled package
- `upload_wheel(wheel_path, repository, dry_run)`: Upload to PyPI

**Design Patterns:**
- Builder pattern for compilation pipeline
- Template method for file processing
- Strategy pattern for repository selection (pypi/testpypi)

### CLI Design
- **Framework**: Typer with automatic help generation
- **Commands**: `compile`, `build`, `upload`
- **Options**: Use long and short forms (e.g., `-o`, `--output`)
- **Defaults**: Safe defaults (e.g., `--dry-run` enabled by default)

### Error Handling
Custom exception hierarchy:
- `PyPIPublisherError`: Base exception
- `CompilationError`: Bytecode compilation failures
- `BuildError`: Wheel building failures  
- `UploadError`: PyPI upload failures

All exceptions support `message`, `details` dict, and `cause` chaining.

## Key Implementation Details

### File Compilation Rules
1. **Always Skip**: `__init__.py`, `_version.py` (kept as source)
2. **Always Skip**: Test files, example files, setup files
3. **Compile**: All other `.py` files to `.pyc`
4. **Binary Extensions**: `.so`, `.pyd` files are preserved

### pyproject.toml Modifications
When compiling, automatically update:
- Add `*.pyc` to `package-data` inclusion
- Add `*.so`, `*.pyd` for binary extensions
- Preserve `py.typed` for type stubs

### Repository URLs
- **PyPI**: `https://upload.pypi.org/legacy/`
- **TestPyPI**: `https://test.pypi.org/legacy/`

## Development Workflow

### Testing
- Use pytest for all tests
- Coverage target: aim for >80%
- Test files: `tests/test_*.py`

### Release Process
1. Update `_version.py`
2. Run tests: `pytest`
3. Run linter: `ruff check src/`
4. Run type check: `mypy src/`
5. Build: `python -m build`
6. Upload: `twine upload dist/*`

## Version Source of Truth (All SageLLM Repos)

**Mandatory unified rule for all Python repos in SageLLM workspace:**

1. **Only one hardcoded version location is allowed**: `src/<package>/_version.py`
2. `pyproject.toml` must use dynamic version:
  - `[project] dynamic = ["version"]`
  - `[tool.setuptools.dynamic] version = {attr = "<package>._version.__version__"}`
3. `src/<package>/__init__.py` must import version from `_version.py`:
  - `from <package>._version import __version__`
4. **Do not hardcode version** in `pyproject.toml` (`project.version`) or `__init__.py`
5. For version bump, update only `_version.py` in each target repo/package.

## Common Tasks

### Adding New CLI Commands
1. Add function to `cli.py` with `@app.command()` decorator
2. Use Typer's `Argument` and `Option` for parameters
3. Use Rich console for output
4. Handle errors with custom exceptions

### Adding Compilation Rules
1. Add logic to `_should_skip_file()` in `compiler.py`
2. Update file pattern matching
3. Add corresponding tests

### Modifying Build Process
1. Update `build_wheel()` method
2. Ensure pyproject.toml adjustments in `_update_pyproject()`
3. Verify wheel contents in `_verify_wheel_contents()`

## Dependencies Management
- **Production**: Minimal dependencies (rich, typer, build, twine)
- **Development**: Add dev tools to `[project.optional-dependencies]`
- **Python Version**: Maintain 3.10+ compatibility
- **Compatibility**: Use `tomli` for Python <3.11 (tomllib backport)

## Environment Policy (Mandatory)
- **Do Not Create venv**: Never create `venv`/`.venv` for this repository or workspace.
- **Use Existing Environment**: Reuse the already activated Python environment (e.g. existing conda env).
- **No Auto Environment Bootstrap**: Do not run environment initialization commands that create new virtual environments.

## Best Practices for Copilot

1. **Type Safety**: Always add type hints for function parameters and returns
2. **Error Messages**: Use descriptive Chinese messages for end users
3. **Progress Feedback**: Use Rich Progress bars for long operations
4. **Dry Run**: Default to safe operations (dry-run mode)
5. **Path Handling**: Use `pathlib.Path` instead of string operations
6. **Context Managers**: Use context managers for file operations and temp directories
7. **Subprocess**: Always capture output and check return codes
8. **Console Output**: Use emoji and color coding for better UX (🔧 📁 ✅ 🚀 ⚠️ ❌)

## Testing Guidelines
- Mock file system operations where appropriate
- Test both success and failure paths
- Test CLI commands using Typer's test utilities
- Verify wheel contents and metadata

## Security Considerations
- Validate all file paths before operations
- Handle symlinks carefully in copytree operations
- Sanitize subprocess inputs
- Use `--skip-existing` for uploads to prevent overwrites

## Internationalization
- User-facing messages: Chinese (Simplified)
- Code/documentation: English
- Error messages: Chinese with technical details in English

## Related Projects
- Extracted from SAGE's internal `sage-dev` tooling
- Designed for IntelliStream Team's monorepo workflow
- MIT licensed, open source

## Repository Information
- **Owner**: intellistream
- **Repository**: sage-pypi-publisher
- **Homepage**: https://github.com/intellistream/pypi-publisher
- **Contact**: shuhao_zhang@hust.edu.cn


## Git Hooks（强制 - Mandatory）

🚨 **所有开发者必须安装 pre-commit 和 pre-push hooks，绝对不允许跳过。**

### 安装要求

1. 克隆仓库后，**第一件事**必须运行 `./quickstart.sh` 安装 Git hooks
2. 如果仓库提供 `hooks/` 目录，必须确保 `.git/hooks/pre-commit` 和 `.git/hooks/pre-push` 已正确链接或复制
3. 每次 `git commit` 和 `git push` 都必须经过 hooks 检查（ruff format / ruff check / pytest 等）

### 禁止绕过 Hooks

- ❌ **禁止** 使用 `git commit --no-verify` 或 `git push --no-verify` 跳过 hooks
- ❌ **禁止** 删除、禁用或修改 `.git/hooks/pre-commit` / `.git/hooks/pre-push`
- ❌ **禁止** 通过任何方式（环境变量、配置等）绕过 hooks 检查
- ⚠️ `--no-verify` 仅在极端特殊情况下允许（如修复 CI 基础设施本身），且必须在 commit message 中注明原因

### Copilot Agent 行为规范

- ✅ 执行 `git commit` 或 `git push` 时，**永远不要**添加 `--no-verify` 标志
- ✅ 如果 hooks 检查失败，必须先修复问题再提交，而不是绕过 hooks
- ✅ 帮助开发者设置 hooks 时，推荐运行 `./quickstart.sh`

## Polyrepo coordination (mandatory)

- This repository is an independent SAGE sub-repository and is developed/released independently.
- Do not assume sibling source directories exist locally in `intellistream/SAGE`.
- For cross-repo rollout, publish this repo/package first, then bump the version pin in `SAGE/packages/sage/pyproject.toml` when applicable.
- Do not add local editable installs of other SAGE sub-packages in setup scripts or docs.
