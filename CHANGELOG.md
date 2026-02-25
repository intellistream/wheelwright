# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Fixed
- CI `Version Source Guard` script indentation corrected in workflow, resolving guard job syntax failure.

### Changed
- **chore: standardize pre-commit hooks** — migrate all checks to `.pre-commit-config.yaml`; replace `hooks/pre-commit` with delegation stub; `./quickstart.sh` and `pre-commit install` are now equivalent

### Added
- 新增 `.github/workflows/ci.yml`，在 PR/Push 上执行 `ruff check src/`
- CI 新增 hooks 保护校验：校验 `pre-commit` / `pre-push` 包含 main 分支保护提示
- CI 新增 `Version Source Guard` 校验：强制 `_version.py` 作为唯一版本源，验证 `dynamic version` 与 `__init__` 导入规则

## [0.1.9.9] - 2026-02-20

### Added
- **`keep_source` 配置支持**：`pyproject.toml` 中的 `[tool.sage-pypi-publisher]` 节现在支持 `keep_source` 列表，允许在 `private` (pyc-only) 模式下保留指定 `.py` 源文件。
  - 用途：Triton 内核等依赖 `inspect.getsourcelines()` 的 JIT 编译器需要运行时可读取 `.py` 源码，通过此选项可在保密发布的同时保留必要的源文件。
  - 配置示例：
    ```toml
    [tool.sage-pypi-publisher]
    keep_source = [
        "src/mypkg/kernels/fused_ops.py",
    ]
    ```
  - 实现：`BytecodeCompiler.__init__` 新增 `keep_source_patterns: list[str]` 参数；`_should_keep_source` 使用 `fnmatch` 匹配；`MANIFEST.in` 和 `setup.py` 自动包含保留的 `.py` 文件。

## [0.1.9.8] - 2026-01-01

### Added
- Initial public release of sage-pypi-publisher
