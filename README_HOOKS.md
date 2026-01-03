# Git Hooks Guide

sage-pypi-publisher 提供了智能的 git hooks，让版本管理和 PyPI 发布变得超级简单！

## 快速开始

### 安装 Hooks

在你的 Python 项目中运行：

```bash
pip install sage-pypi-publisher
sage-pypi-publisher install-hooks .
```

✓ 完成！现在你的 repo 已经配置好了自动化工作流。

## 功能特性

### 🎯 自动版本检测

当你更新 `pyproject.toml` 中的版本号并 push 时，hook 会：
1. 检测到版本变化
2. 询问是否要构建并上传到 PyPI
3. 自动使用 sage-pypi-publisher 构建（智能检测是否需要 manylinux）
4. 上传到 PyPI
5. Push 到 GitHub

### 📝 交互式版本更新

如果你忘记更新版本就 push，hook 会：
1. 提醒你版本没有更新
2. 提供交互式版本更新选项
3. 自动修改 `pyproject.toml`
4. 创建版本更新 commit
5. 可选：立即构建并上传到 PyPI

### 🔧 智能构建

Hook 集成了 sage-pypi-publisher 的智能检测：
- **C/C++ 扩展包**：自动构建 manylinux wheel
- **纯 Python 包**：构建标准 wheel

## 使用示例

### 场景 1：正常版本更新流程

```bash
# 1. 修改代码
vim src/mypackage/main.py

# 2. 更新版本号
vim pyproject.toml  # version = "0.1.3" -> "0.1.4"

# 3. 提交
git add .
git commit -m "feat: add new feature"

# 4. Push
git push
```

Hook 会提示：
```
✓ Version updated to 0.1.4
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 Build and upload version 0.1.4 to PyPI?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [y] Yes, build and upload to PyPI
  [n] No, just push to GitHub
  [c] Cancel push
Your choice [y/n/c]: 
```

选择 `y` → 自动构建并上传！

### 场景 2：忘记更新版本

```bash
# 1. 修改代码
vim src/mypackage/main.py

# 2. 提交（忘记更新版本）
git add .
git commit -m "feat: add new feature"

# 3. Push
git push
```

Hook 会提示：
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠  WARNING: Version not updated!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 Current version: 0.1.3

What would you like to do?
  [u] Update version now (interactive)
  [y] Continue without version update
  [n] Cancel push
Your choice [u/y/n]: 
```

选择 `u` → 交互式输入新版本：
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 Version Update
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Current: 0.1.3

Enter new version (e.g., 0.1.4, 1.0.0):
New version: 0.1.4

✓ 0.1.3 → 0.1.4

📦 Build and upload to PyPI? [y/n]: y
```

Hook 会自动：
1. 更新 `pyproject.toml`
2. 创建版本 commit
3. 构建并上传到 PyPI
4. Push 所有更改

## 工作原理

```
┌─────────────────┐
│   git push      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ 检测 pyproject.toml 中   │
│ 的版本是否更新           │
└────────┬────────────────┘
         │
    ┌────┴─────┐
    │          │
YES │          │ NO
    │          │
    ▼          ▼
┌────────┐  ┌──────────────┐
│提示上传│  │提示交互式更新│
│到 PyPI │  │或继续 push   │
└───┬────┘  └──────┬───────┘
    │              │
    │         ┌────┴────┐
    │         │ 用户选择 │
    │         └────┬────┘
    │              │
    │       ┌──────┴───────┐
    │       │              │
    │    [u]更新        [y]继续
    │       │              │
    │       ▼              │
    │  ┌─────────┐         │
    │  │自动更新版│         │
    │  │本并commit│         │
    │  └────┬────┘         │
    │       │              │
    └───────┴──────────────┘
            │
            ▼
    ┌──────────────┐
    │ Push 到 GitHub│
    └──────────────┘
```

## 卸载 Hooks

如果需要移除 hooks：

```bash
sage-pypi-publisher uninstall-hooks .
```

如果之前有 pre-push hook，会自动恢复备份。

## 技术细节

### Hook 位置
`.git/hooks/pre-push`

### 备份
安装时会自动备份现有的 pre-push hook 到 `.git/hooks/pre-push.backup`

### 版本检测
检查最近 5 个 commits 中 `pyproject.toml` 的 version 字段变化

### 构建方式
- 检测到 `scikit-build-core`、`pybind11`、`CMakeLists.txt` → manylinux wheel
- 纯 Python 包 → 标准 wheel + 字节码编译（可选）

## 常见问题

### Q: Hook 会影响普通的 git push 吗？
A: 不会。如果没有更新版本，选择 `[y] Continue` 即可正常 push。

### Q: 可以跳过 PyPI 上传吗？
A: 可以。检测到版本更新时选择 `[n] No, just push to GitHub`。

### Q: 支持哪些包类型？
A: 
- ✅ 纯 Python 包
- ✅ C/C++ 扩展包（自动 manylinux）
- ✅ 混合包

### Q: 支持 testpypi 吗？
A: 当前默认上传到 pypi。如需 testpypi，可修改 hook 中的 `--repository` 参数。

### Q: 如何自定义 manylinux 标签？
A: 修改 hook 中的 `sage-pypi-publisher build` 命令，添加 `--platform` 参数。

## 最佳实践

1. **在项目初始化时安装**
   ```bash
   sage-pypi-publisher install-hooks .
   git add .git/hooks/pre-push  # 可选：将 hook 加入版本控制
   ```

2. **团队使用**
   每个开发者安装 sage-pypi-publisher 后运行 `install-hooks`

3. **CI/CD 集成**
   Hook 主要用于开发环境。CI/CD 可以直接调用 `sage-pypi-publisher build`

4. **语义化版本**
   遵循 [SemVer](https://semver.org/)：
   - `0.0.x` - Bug fixes
   - `0.x.0` - New features (backward compatible)
   - `x.0.0` - Breaking changes

## 相关链接

- [sage-pypi-publisher GitHub](https://github.com/intellistream/sage-pypi-publisher)
- [PyPI 项目页](https://pypi.org/project/sage-pypi-publisher/)

## 反馈

有问题或建议？欢迎提 issue 或 PR！
