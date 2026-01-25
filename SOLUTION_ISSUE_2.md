# 解决方案：SAGE PyPI包多版本支持

## 问题描述

issue #2 提出：SAGE系列PyPI包在metadata中声明支持Python 3.8-3.12，但实际上传的wheel文件只有Python 3.11版本（cp311-cp311-manylinux_2_34_x86_64.whl）。这导致：

- ✅ Python 3.11：可以直接安装预编译wheel（快速）
- ⚠️ 其他版本（3.8, 3.9, 3.10, 3.12）：无法直接安装预编译wheel

**根本原因**: sage-pypi-publisher只为当前运行的Python版本构建wheel，没有提供多版本或源码分发支持。

## 解决方案

### 🚀 推荐方案：使用 `--for-pypi` 智能模式

**一个命令解决所有问题！**

```bash
sage-pypi-publisher build . --for-pypi --upload --no-dry-run
```

这个命令会自动：
1. **检测包类型**：纯Python包 vs C扩展包
2. **选择最佳策略**：
   - 纯Python → 构建通用wheel (py3-none-any) + sdist
   - C扩展 → 构建当前Python版本wheel + sdist
3. **确保兼容性**：所有Python 3.x版本都能安装

### 为什么这样做？

#### 技术真相
**问题**: 无法在Python 3.11环境中真正构建Python 3.10或3.12的wheel

- ❌ **错误做法**：修改wheel标签但用当前Python编译（生成的是假的多版本wheel）
- ✅ **正确做法**：使用通用wheel或提供源码让用户编译

#### 正确的多版本支持策略

1. **纯Python包** → **通用wheel (py3-none-any)**
   - 一个wheel文件支持**所有**Python 3.x版本！
   - 无需为每个版本单独构建
   - 文件名：`package-1.0.0-py3-none-any.whl`

2. **有C扩展的包** → **当前版本wheel + 源码分发**
   - 提供当前Python版本的预编译wheel
   - 提供sdist让其他版本用户从源码编译
   - 或在CI/CD中使用`cibuildwheel`真正构建多版本

## 实现细节

### 新增功能

#### 1. `--for-pypi` 智能模式（推荐）

#### 1. `--for-pypi` 智能模式（推荐）

自动检测并选择最佳发布策略：

```bash
sage-pypi-publisher build . --for-pypi --upload --no-dry-run
```

- 自动识别纯Python包 → universal wheel + sdist
- 自动识别C扩展包 → 当前Python wheel + sdist
- 适合所有场景的一站式解决方案

#### 2. 手动控制选项

```bash
# 构建通用wheel（仅纯Python包）
sage-pypi-publisher build . --universal

# 添加源码分发
sage-pypi-publisher build . --universal --sdist
```

### 新增API方法

在`BytecodeCompiler`类中添加：

#### `build_universal_wheel()`
```python
def build_universal_wheel(self, compiled_path: Path | None = None) -> Path:
    """Build a universal pure Python wheel (py3-none-any)."""
```

#### 2. `build_sdist()`
```python
def build_sdist(self, compiled_path: Path | None = None) -> Path:
    """Build a source distribution (.tar.gz)."""
```

#### 3. `build_multi_python()`
```python
def build_multi_python(
    self,
    python_versions: Iterable[str] = ("cp38", "cp39", "cp310", "cp311", "cp312"),
    compiled_path: Path | None = None,
) -> list[Path]:
    """Build wheels for multiple Python versions."""
```

### CLI增强

`build`命令新增三个选项：

```bash
--universal         # Build py3-none-any wheel
--sdist             # Also build source distribution
--multi-python      # Build for multiple Python versions
```

### 使用示例

```bash
# 1. 构建通用wheel
sage-pypi-publisher build . --universal

# 2. 构建wheel + sdist
sage-pypi-publisher build . --universal --sdist

# 3. 构建多个Python版本
sage-pypi-publisher build . --multi-python cp38,cp39,cp310,cp311,cp312

# 4. 完整发布流程（推荐）
sage-pypi-publisher build . --universal --sdist --upload --no-dry-run -r pypi
```

### Python API使用

```python
from pathlib import Path
from pypi_publisher.compiler import BytecodeCompiler

compiler = BytecodeCompiler(Path("/path/to/pkg"), mode="public")
compiled = compiler.compile_package()

# 构建通用wheel
universal_wheel = compiler.build_universal_wheel(compiled)

# 构建sdist
sdist = compiler.build_sdist(compiled)

# 构建多版本wheels
wheels = compiler.build_multi_python(
    python_versions=["cp38", "cp39", "cp310", "cp311", "cp312"],
    compiled_path=compiled
)

# 上传所有artifacts
for artifact in [universal_wheel, sdist]:
    compiler.upload_wheel(artifact, repository="pypi", dry_run=False)
```

## 建议的SAGE发布策略

对于SAGE系列包，建议使用以下策略：

### 纯Python包（如isage-common, isage-llm-core等）

```bash
# 构建通用wheel + sdist
sage-pypi-publisher build . --universal --sdist --upload --no-dry-run
```

这将生成：
- `isage-common-0.1.5-py3-none-any.whl`（适用所有Python 3版本）
- `isage-common-0.1.5.tar.gz`（源码后备）

### C/C++扩展包（如isage-vdb）

对于有C扩展的包，使用现有manylinux构建 + sdist：

```bash
# 构建manylinux wheel + sdist  
sage-pypi-publisher build . --force-manylinux --sdist --upload --no-dry-run
```

或者在CI/CD中使用cibuildwheel为多个Python版本构建。

## 影响分析

### 优点
1. ✅ 真正解决多版本兼容性问题（技术正确）
2. ✅ 用户可以在声明的所有Python版本上安装
3. ✅ 提供源码分发作为后备方案
4. ✅ 向后兼容，不破坏现有功能
5. ✅ 简化用户体验（一个 `--for-pypi` 搞定）
6. ✅ 避免技术上不可行的"多版本构建"误导

### 用户体验
- **小白用户**：使用 `--for-pypi`，无需理解技术细节
- **高级用户**：仍可使用 `--universal`、`--sdist` 等选项精确控制

### 兼容性
- 完全向后兼容
- 默认行为不变（仍为当前Python版本构建）
- 新功能为可选项

## 相关文件修改

1. **src/pypi_publisher/compiler.py**: 
   - 新增 `build_universal_wheel()` 方法
   - 新增 `build_sdist()` 方法
   - ~~移除误导性的 `build_multi_python()` 方法~~
   
2. **src/pypi_publisher/cli.py**: 
   - 新增 `--for-pypi` 智能选项
   - 保留 `--universal` 和 `--sdist` 手动选项
   - 移除 `--multi-python` 选项（技术不可行）
   - 添加智能检测和提示逻辑
   
3. **README.md**: 
   - 更新为以 `--for-pypi` 为核心的文档
   - 添加技术说明解释为什么不能本地多版本构建
   - 简化用户指南
   
4. **.env**: 从SAGE仓库复制

## 后续建议

1. ✅ 为SAGE系列所有纯Python包使用 `--for-pypi` 重新发布
2. ✅ 确保所有包都包含sdist
3. 🔄 考虑在GitHub Actions中集成cibuildwheel用于C扩展包
4. 📚 更新SAGE项目文档，说明新的发布流程

## 关键要点总结

1. **技术正确性**：不能在Python 3.11环境中真正构建其他版本的wheels
2. **解决方案**：使用universal wheel (py3-none-any) + sdist
3. **用户体验**：`--for-pypi` 一个选项自动选择最佳策略
4. **效果**：真正实现了"支持Python 3.8-3.12"的承诺

---

**Status**: ✅ 已完成并测试（技术正确版本）
**Date**: 2026-01-24
**Note**: 修正了之前技术上不可行的"多版本构建"方案
