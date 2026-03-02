"""
Bytecode compiler and PyPI publisher toolkit.

Ported from SAGE dev tools, generalized for any Python package directory.
"""

from __future__ import annotations

import fnmatch
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from rich.console import Console
from rich.progress import Progress

from pypi_publisher.exceptions import BuildError, CompilationError, UploadError

console = Console()

# Build modes
BuildMode = Literal["private", "public", "bytecode", "source"]


class BytecodeCompiler:
    """Compile a Python package to bytecode, build a wheel, and optionally upload."""

    def __init__(
        self,
        package_path: Path,
        temp_dir: Path | None = None,
        mode: BuildMode = "private",
        keep_source_patterns: list[str] | None = None,
    ):
        self.package_path = Path(package_path)
        self.temp_dir = temp_dir
        self.compiled_path: Path | None = None
        self._binary_extensions: list[Path] = []
        # Glob patterns (relative to package root) whose .py files are preserved
        # even in private mode, e.g. ["src/mypkg/kernels/fused_ops.py"]
        self.keep_source_patterns: list[str] = keep_source_patterns or []

        # Normalize mode: private/bytecode → private, public/source → public
        if mode in ("private", "bytecode"):
            self.mode: Literal["private", "public"] = "private"
        elif mode in ("public", "source"):
            self.mode = "public"
        else:
            raise CompilationError(
                f"Invalid build mode: {mode}. Must be 'private', 'public', 'bytecode', or 'source'."
            )

        if not self.package_path.exists():
            raise CompilationError(f"Package path does not exist: {package_path}")
        if not self.package_path.is_dir():
            raise CompilationError(f"Package path is not a directory: {package_path}")

    # Public API
    def compile_package(self, output_dir: Path | None = None) -> Path:
        """Copy the package, compile .py -> .pyc (if private mode), update pyproject for package data."""
        mode_emoji = "🔒" if self.mode == "private" else "📖"
        mode_name = "保密模式 (字节码)" if self.mode == "private" else "公开模式 (源码)"
        console.print(f"{mode_emoji} 构建包: {self.package_path.name} - {mode_name}", style="cyan")

        if output_dir:
            self.temp_dir = Path(output_dir)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.temp_dir = Path(
                tempfile.mkdtemp(prefix=f"pypi_publisher_{self.package_path.name}_")
            )

        self.compiled_path = self.temp_dir / self.package_path.name
        console.print(f"📁 复制项目结构到: {self.compiled_path}")

        # Remove existing compiled path if it exists (from previous builds)
        if self.compiled_path.exists():
            console.print(f"  🧹 清理已存在的目录: {self.compiled_path}")
            shutil.rmtree(self.compiled_path)
        shutil.copytree(self.package_path, self.compiled_path, symlinks=True)

        if self.mode == "private":
            # Private mode: compile to bytecode
            self._compile_python_files()
            self._remove_source_files()
            self._update_pyproject()
            console.print(f"✅ 包编译完成 (保密模式): {self.package_path.name}", style="green")
        else:
            # Public mode: keep source files as-is
            console.print("  📝 保留所有Python源文件 (公开模式)", style="cyan")
            self._update_pyproject_public()
            console.print(f"✅ 包准备完成 (公开模式): {self.package_path.name}", style="green")

        return self.compiled_path

    def build_wheel(self, compiled_path: Path | None = None, python_tag: str | None = None) -> Path:
        """Build wheel from compiled path with optional specific Python tag."""
        target_path = compiled_path or self.compiled_path
        if not target_path:
            raise BuildError("Package not compiled yet. Call compile_package() first.")

        console.print(f"📦 构建wheel包: {target_path.name}", style="cyan")
        original_dir = Path.cwd()
        os.chdir(target_path)
        try:
            for build_dir in ["dist", "build"]:
                if Path(build_dir).exists():
                    shutil.rmtree(build_dir)
                    console.print(f"  🧹 清理目录: {build_dir}")

            pyc_files = list(Path(".").rglob("*.pyc"))
            if pyc_files:
                console.print(f"  📊 找到 {len(pyc_files)} 个.pyc文件")

            # Use provided python_tag or auto-detect from current Python
            if python_tag is None:
                major, minor = sys.version_info.major, sys.version_info.minor
                python_tag = f"cp{major}{minor}"

            console.print("  🔨 构建wheel (setuptools bdist_wheel)...")
            console.print(f"  🏷️  使用Python标签: {python_tag}", style="dim")

            build_cmd = [sys.executable, "setup.py", "bdist_wheel", f"--python-tag={python_tag}"]
            result = subprocess.run(build_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "构建失败"
                raise BuildError(error_msg, package_name=target_path.name)

            dist_files = list(Path("dist").glob("*.whl"))
            if not dist_files:
                raise BuildError("构建完成但未找到wheel文件", package_name=target_path.name)

            wheel_file = dist_files[0]
            console.print(f"    📄 {wheel_file.name} ({wheel_file.stat().st_size / 1024:.2f} KB)")
            self._verify_wheel_contents(wheel_file)
            return wheel_file.resolve()
        finally:
            os.chdir(original_dir)

    def upload_wheel(
        self,
        wheel_path: Path,
        repository: str = "pypi",
        dry_run: bool = True,
        auto_push: bool = False,
    ) -> bool:
        repo_name = "TestPyPI" if repository == "testpypi" else "PyPI"
        console.print(f"  🚀 上传到{repo_name}...", style="cyan")

        wheel_files = [str(wheel_path)]
        if not wheel_files:
            raise UploadError("未找到 wheel 文件", repository=repo_name)

        if dry_run:
            console.print("  🔍 预演模式：跳过上传", style="yellow")
            for wf in wheel_files:
                console.print(f"    • {Path(wf).name}")
            return True

        cmd = ["twine", "upload", "--skip-existing"]
        if repository == "testpypi":
            cmd.extend(["--repository", "testpypi"])
        cmd.extend(wheel_files)

        try:
            upload_result = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise UploadError(
                "未找到 twine，请先安装 (pip install twine)", repository=repo_name
            ) from exc

        if upload_result.returncode == 0:
            # 解析输出，区分真正上传和跳过
            output = upload_result.stdout + upload_result.stderr

            # 检测是否包含 "Skipping" 或 "File already exists"
            has_skipped = bool(
                re.search(
                    r"(Skipping|File already exists|already been uploaded)", output, re.IGNORECASE
                )
            )
            # 检测是否有真正的上传
            has_uploaded = bool(re.search(r"(Uploading|Uploaded)", output, re.IGNORECASE))

            if has_uploaded and not has_skipped:
                # 完全新上传
                console.print(f"  ✅ 已上传新版本到{repo_name}", style="green bold")
            elif has_skipped and not has_uploaded:
                # 全部跳过
                console.print("  ℹ️  版本已存在，跳过上传", style="yellow")
                console.print(f"    提示：无需重新上传，{repo_name}已有此版本", style="dim")
            elif has_uploaded and has_skipped:
                # 部分上传，部分跳过
                console.print("  ⚠️  部分文件已上传，部分已存在", style="yellow")
            else:
                # 无法判断，使用原来的提示
                console.print(f"  ✅ 上传到{repo_name}成功", style="green")

            # 重要提示：只上传了 PyPI，还需要推送到 GitHub
            # 如果从 pre-push hook 调用（SAGE_PYPI_PUBLISHER_PUSHING 或 GIT_PUSH_OPTION_COUNT 环境变量存在）
            # 或者 auto_push=True，则不显示此提示，因为代码会被推送
            from_prepush_hook = os.environ.get("GIT_PUSH_OPTION_COUNT") is not None
            if not auto_push and not from_prepush_hook:
                console.print(
                    f"\n  💡 [yellow]注意：仅上传到{repo_name}，代码尚未推送到 GitHub[/yellow]"
                )
                console.print("     [dim]（请手动执行 git push 或使用 --auto-push 选项）[/dim]")

            # 显示 PyPI 链接
            if upload_result.stdout:
                for line in upload_result.stdout.split("\n"):
                    if "View at:" in line or ("https://" in line and "pypi.org" in line):
                        console.print(f"    🔗 {line.strip()}", style="cyan")

            # Auto-push to GitHub if enabled and in a git repository
            if auto_push:
                self._auto_push_to_github()

            return True

        error_msg = upload_result.stderr.strip() if upload_result.stderr else "未知错误"
        raise UploadError(error_msg[:200], repository=repo_name)

    def build_universal_wheel(self, compiled_path: Path | None = None) -> Path:
        """Build a universal pure Python wheel (py3-none-any).

        This is suitable for pure Python packages without C extensions.
        The wheel will be compatible with all Python 3 versions.
        """
        target_path = compiled_path or self.compiled_path
        if not target_path:
            raise BuildError("Package not compiled yet. Call compile_package() first.")

        console.print(f"🌍 构建通用wheel包 (py3-none-any): {target_path.name}", style="cyan")
        original_dir = Path.cwd()
        os.chdir(target_path)
        try:
            # Only clean build directory, keep dist for multiple builds
            if Path("build").exists():
                shutil.rmtree("build")
                console.print("  🧹 清理目录: build")

            # Ensure dist directory exists
            Path("dist").mkdir(exist_ok=True)

            console.print("  🔨 构建通用wheel...")
            build_cmd = [sys.executable, "setup.py", "bdist_wheel", "--universal"]
            result = subprocess.run(build_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "构建失败"
                raise BuildError(error_msg, package_name=target_path.name)

            dist_files = list(Path("dist").glob("*.whl"))
            if not dist_files:
                raise BuildError("构建完成但未找到wheel文件", package_name=target_path.name)

            wheel_file = dist_files[0]
            console.print(f"    📄 {wheel_file.name} ({wheel_file.stat().st_size / 1024:.2f} KB)")
            console.print("    ✓ 该wheel支持所有Python 3版本", style="green")
            return wheel_file.resolve()
        finally:
            os.chdir(original_dir)

    def build_sdist(self, compiled_path: Path | None = None) -> Path:
        """Build a source distribution (.tar.gz).

        Source distributions allow users to install from source and are
        compatible with any Python version.
        """
        target_path = compiled_path or self.compiled_path
        if not target_path:
            raise BuildError("Package not compiled yet. Call compile_package() first.")

        console.print(f"📚 构建源码分发包 (sdist): {target_path.name}", style="cyan")
        original_dir = Path.cwd()
        os.chdir(target_path)
        try:
            # Only clean build directory, keep dist for multiple builds
            if Path("build").exists():
                shutil.rmtree("build")
                console.print("  🧹 清理目录: build")

            # Ensure dist directory exists
            Path("dist").mkdir(exist_ok=True)

            console.print("  🔨 构建sdist...")
            build_cmd = [sys.executable, "setup.py", "sdist"]
            result = subprocess.run(build_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "构建失败"
                raise BuildError(error_msg, package_name=target_path.name)

            dist_files = list(Path("dist").glob("*.tar.gz"))
            if not dist_files:
                raise BuildError("构建完成但未找到sdist文件", package_name=target_path.name)

            sdist_file = dist_files[0]
            console.print(f"    📄 {sdist_file.name} ({sdist_file.stat().st_size / 1024:.2f} KB)")
            console.print("    ✓ 源码分发包可在所有Python版本上安装", style="green")
            return sdist_file.resolve()
        finally:
            os.chdir(original_dir)

    def _compile_python_files(self) -> None:
        assert self.compiled_path
        python_files = list(self.compiled_path.rglob("*.py"))
        files_to_compile: list[Path] = []
        skipped_count = 0
        for py_file in python_files:
            if self._should_skip_file(py_file):
                skipped_count += 1
                continue
            files_to_compile.append(py_file)

        if not files_to_compile:
            console.print("  ⚠️ 没有找到需要编译的Python文件", style="yellow")
            return

        console.print(
            f"  📝 找到 {len(files_to_compile)} 个Python文件需要编译 (跳过 {skipped_count} 个)"
        )
        self._preserve_binary_extensions()
        with Progress() as progress:
            task = progress.add_task("编译Python文件", total=len(files_to_compile))
            failed_files: list[tuple[Path, str]] = []
            for py_file in files_to_compile:
                try:
                    pyc_file = py_file.with_suffix(".pyc")
                    # Calculate clean relative path for co_filename to avoid leaking build paths
                    # and ensure clean tracebacks on user machines
                    rel_path = py_file.relative_to(self.compiled_path)

                    # If using src-layout, strip the src/ prefix to match installation structure
                    clean_path = str(rel_path)
                    parts = rel_path.parts
                    if parts[0] == "src" and len(parts) > 1:
                        clean_path = str(Path(*parts[1:]))

                    py_compile.compile(str(py_file), str(pyc_file), dfile=clean_path, doraise=True)
                except Exception as e:  # noqa: BLE001
                    failed_files.append((py_file.relative_to(self.compiled_path), str(e)))
                progress.update(task, advance=1)

        if failed_files:
            console.print("  ❌ 编译失败的文件:", style="red")
            for file_path, error in failed_files:
                console.print(f"     - {file_path}: {error[:120]}", style="red")
            raise CompilationError(
                f"字节码编译失败：{len(failed_files)} 个文件编译出错，已中止构建。"
                " 修复上述文件后重试。",
                details={
                    "failed_count": len(failed_files),
                    "files": [str(f) for f, _ in failed_files],
                },
            )

    def _preserve_binary_extensions(self) -> None:
        assert self.compiled_path
        extensions: list[Path] = []
        for ext in ["*.so", "*.pyd", "*.dylib"]:
            extensions.extend(self.compiled_path.rglob(ext))
        self._binary_extensions = extensions
        if extensions:
            console.print(f"  🔧 找到 {len(extensions)} 个二进制扩展文件")
        else:
            console.print("  ℹ️ 未找到二进制扩展文件", style="dim")

    def _should_skip_file(self, py_file: Path) -> bool:
        skip_files = ["setup.py", "conftest.py"]
        if py_file.name in skip_files:
            return True
        file_str = str(py_file)
        if "/tests/" in file_str or file_str.endswith("/tests"):
            return True
        if py_file.name.startswith("test_") or py_file.name.endswith("_test.py"):
            return True
        return False

    def _remove_source_files(self) -> None:
        assert self.compiled_path
        python_files = list(self.compiled_path.rglob("*.py"))
        removed = kept = 0
        orphaned: list[Path] = []
        console.print("  🗑️ 清理源文件...")
        for py_file in python_files:
            if self._should_keep_source(py_file):
                kept += 1
                continue
            # Files intentionally skipped from compilation (tests, conftest, etc.)
            # should be removed from the wheel entirely — no .pyc expected.
            if self._should_skip_file(py_file):
                py_file.unlink()
                removed += 1
                continue
            pyc_file = py_file.with_suffix(".pyc")
            if pyc_file.exists():
                py_file.unlink()
                removed += 1
            else:
                # .pyc missing for a non-skipped file means compilation silently failed —
                # this is the bug case; fail fast.
                orphaned.append(py_file.relative_to(self.compiled_path))
        if orphaned:
            console.print("  ❌ 以下源文件没有对应 .pyc（编译步骤遗漏或失败）:", style="red")
            for p in orphaned:
                console.print(f"     - {p}", style="red")
            raise CompilationError(
                f"构建中止：{len(orphaned)} 个文件缺少 .pyc，无法安全删除源码。"
                " 请检查编译步骤是否正确完成。",
                details={"orphaned_count": len(orphaned), "files": [str(p) for p in orphaned]},
            )
        console.print(f"  📊 清理统计: 删除 {removed}, 保留 {kept}")

    def _should_keep_source(self, py_file: Path) -> bool:
        keep_files = ["setup.py", "_version.py", "__init__.py"]
        if py_file.name in keep_files:
            return True
        if self.keep_source_patterns and self.compiled_path:
            # Match against path relative to the compiled package directory
            rel = str(py_file.relative_to(self.compiled_path)).replace(os.sep, "/")
            for pattern in self.keep_source_patterns:
                pat = pattern.replace(os.sep, "/")
                if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(py_file.name, pat):
                    return True
        return False

    def _update_pyproject(self) -> None:
        assert self.compiled_path
        pyproject_file = self.compiled_path / "pyproject.toml"
        if not pyproject_file.exists():
            console.print("  ⚠️ 未找到pyproject.toml文件", style="yellow")
            return

        content = pyproject_file.read_text(encoding="utf-8")

        # Set exact Python version constraint for bytecode compatibility
        major, minor = sys.version_info.major, sys.version_info.minor
        exact_version = f"=={major}.{minor}.*"

        requires_python_pattern = r'(requires-python\s*=\s*["\'])([^"\']+)(["\'])'
        if re.search(requires_python_pattern, content):
            old_content = content
            content = re.sub(requires_python_pattern, rf"\1{exact_version}\3", content)
            if content != old_content:
                console.print(
                    f"  🐍 设置Python版本约束: {exact_version} (字节码兼容)", style="yellow"
                )
        else:
            # Add requires-python to [project] section if missing
            project_pattern = r"(\[project\][^\[]*?)((?=\[)|$)"
            match = re.search(project_pattern, content, re.DOTALL)
            if match:
                project_section = match.group(1)
                if "requires-python" not in project_section:
                    updated_section = (
                        project_section.rstrip() + f'\nrequires-python = "{exact_version}"\n'
                    )
                    content = content.replace(project_section, updated_section)
                    console.print(
                        f"  🐍 添加Python版本约束: {exact_version} (字节码兼容)", style="yellow"
                    )

        uses_scikit_build = "scikit_build_core" in content
        if uses_scikit_build:
            console.print("  🔧 检测到 scikit-build-core，切换到 setuptools", style="yellow")
            content = re.sub(
                r"build-backend\s*=\s*[\"\']scikit_build_core\.build[\"\']",
                'build-backend = "setuptools.build_meta"',
                content,
            )
            content = re.sub(
                r"\[build-system\][\s\S]*?(?=\n\[)",
                '[build-system]\nrequires = ["setuptools>=64", "wheel"]\nbuild-backend = "setuptools.build_meta"\n\n',
                content,
            )
            content = re.sub(r"\[tool\.scikit-build\][\s\S]*?(?=\n\[|\Z)", "", content)
            content = re.sub(r"\[tool\.scikit-build\..*?\][\s\S]*?(?=\n\[|\Z)", "", content)

        has_packages_list = "packages = [" in content
        has_packages_find = "[tool.setuptools.packages.find]" in content
        has_pyc_package_data = '"*.pyc"' in content and "[tool.setuptools.package-data]" in content
        has_include_package_data = "include-package-data = true" in content.lower()
        modified = False

        if not has_packages_list and not has_packages_find:
            content += """
[tool.setuptools.packages.find]
where = ["src"]
"""
            modified = True

        if not has_include_package_data:
            if "[tool.setuptools]" in content:
                pattern = r"(\[tool\.setuptools\][\s\S]*?)(?=\n\[|\n$|$)"
                match = re.search(pattern, content)
                if match:
                    existing_section = match.group(1)
                    if "include-package-data" not in existing_section:
                        updated = existing_section.rstrip() + "\ninclude-package-data = true\n"
                        content = content.replace(existing_section, updated)
                        modified = True
            else:
                content += """
[tool.setuptools]
include-package-data = true
"""
                modified = True

        if not has_pyc_package_data:
            if "[tool.setuptools.package-data]" in content:
                pattern = r"(\[tool\.setuptools\.package-data\][\s\S]*?)(?=\n\[|\n$|$)"
                match = re.search(pattern, content)
                if match:
                    existing_data = match.group(1)
                    if '"*.pyc"' not in existing_data:
                        star_pattern = r'"(\*)" = \[([^\]]*)\]'
                        star_matches = list(re.finditer(star_pattern, existing_data, re.MULTILINE))
                        if star_matches:
                            all_items: list[str] = []
                            for m in star_matches:
                                items = m.group(2).strip()
                                if items:
                                    for item in items.split(","):
                                        item = item.strip().strip('"').strip("'")
                                        if item and item not in all_items:
                                            all_items.append(item)
                            for pattern_item in [
                                "*.pyc",
                                "*.pyo",
                                "__pycache__/*",
                                "*.so",
                                "*.pyd",
                                "*.dylib",
                            ]:
                                if pattern_item not in all_items:
                                    all_items.append(pattern_item)
                            formatted_items = ",\n    ".join(f'"{it}"' for it in all_items)
                            updated_line = f'"*" = [\n    {formatted_items},\n]'
                            updated_data = existing_data.replace(
                                star_matches[0].group(0), updated_line
                            )
                            for m in star_matches[1:]:
                                updated_data = updated_data.replace(m.group(0), "")
                            updated_data = re.sub(r"\n\s*\n\s*\n", "\n\n", updated_data)
                        else:
                            updated_data = (
                                existing_data.rstrip()
                                + '\n"*" = ["*.pyc", "*.pyo", "__pycache__/*", "*.so", "*.pyd", "*.dylib"]\n'
                            )
                        content = content.replace(existing_data, updated_data)
                        modified = True
            else:
                content += """
[tool.setuptools.package-data]
"*" = ["*.pyc", "*.pyo", "__pycache__/*", "*.so", "*.pyd", "*.dylib"]
"""
                modified = True

        content = re.sub(r"\n\n\n+", "\n\n", content)

        manifest_lines = [
            "# Include compiled files and binary extensions",
            "recursive-include src *.pyc",
            "recursive-include src *.pyo",
            "recursive-include src __pycache__/*",
            "recursive-include src *.so",
            "recursive-include src *.pyd",
            "recursive-include src *.dylib",
        ]
        if self.keep_source_patterns:
            manifest_lines.append("# Kept .py source files (required by JIT compilers e.g. Triton)")
            for pat in self.keep_source_patterns:
                manifest_lines.append(f"global-include {pat}")
        manifest_file = self.compiled_path / "MANIFEST.in"
        manifest_file.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")

        # Build package_data patterns for setup.py
        _pkg_data_items = [
            '"*.pyc"',
            '"*.pyo"',
            '"__pycache__/*"',
            '"*.so"',
            '"*.pyd"',
            '"*.dylib"',
        ]
        if self.keep_source_patterns:
            _pkg_data_items.append('"*.py"')  # keep all kept .py accessible under package data
        _pkg_data_str = ", ".join(_pkg_data_items)

        setup_py_file = self.compiled_path / "setup.py"
        setup_py_file.write_text(
            f"""
from setuptools import setup

setup(
    include_package_data=True,
    package_data={{
        "": [{_pkg_data_str}],
    }},
)
""",
            encoding="utf-8",
        )

        if modified or uses_scikit_build:
            pyproject_file.write_text(content, encoding="utf-8")
            console.print("  ✅ 更新pyproject.toml配置", style="green")
        else:
            console.print("  ✓ pyproject.toml配置已满足要求", style="dim")

    def _update_pyproject_public(self) -> None:
        """Update pyproject.toml for public mode (source distribution)."""
        assert self.compiled_path
        pyproject_file = self.compiled_path / "pyproject.toml"
        if not pyproject_file.exists():
            console.print("  ⚠️ 未找到pyproject.toml文件", style="yellow")
            return

        content = pyproject_file.read_text(encoding="utf-8")
        modified = False

        # For public mode, don't set strict Python version (bytecode not an issue)
        console.print("  📝 公开模式：保持原有Python版本要求", style="dim")

        # Switch from scikit-build to setuptools if needed
        uses_scikit_build = "scikit_build_core" in content
        if uses_scikit_build:
            console.print("  🔧 检测到 scikit-build-core，切换到 setuptools", style="yellow")
            content = re.sub(
                r"build-backend\s*=\s*[\"\']scikit_build_core\.build[\"\']",
                'build-backend = "setuptools.build_meta"',
                content,
            )
            content = re.sub(
                r"\[build-system\][\s\S]*?(?=\n\[)",
                '[build-system]\nrequires = ["setuptools>=64", "wheel"]\nbuild-backend = "setuptools.build_meta"\n\n',
                content,
            )
            content = re.sub(r"\[tool\.scikit-build\][\s\S]*?(?=\n\[|\Z)", "", content)
            content = re.sub(r"\[tool\.scikit-build\..*?\][\s\S]*?(?=\n\[|\Z)", "", content)
            modified = True

        # Ensure packages are discoverable
        has_packages_list = "packages = [" in content
        has_packages_find = "[tool.setuptools.packages.find]" in content

        if not has_packages_list and not has_packages_find:
            content += """
[tool.setuptools.packages.find]
where = ["src"]
"""
            modified = True

        # For public mode, ensure source files are included
        has_include_package_data = "include-package-data = true" in content.lower()
        if not has_include_package_data:
            if "[tool.setuptools]" in content:
                pattern = r"(\[tool\.setuptools\][\s\S]*?)(?=\n\[|\n$|$)"
                match = re.search(pattern, content)
                if match:
                    existing_section = match.group(1)
                    if "include-package-data" not in existing_section:
                        updated = existing_section.rstrip() + "\ninclude-package-data = true\n"
                        content = content.replace(existing_section, updated)
                        modified = True
            else:
                content += """
[tool.setuptools]
include-package-data = true
"""
                modified = True

        content = re.sub(r"\n\n\n+", "\n\n", content)

        # Create a simple setup.py for source distribution
        setup_py_file = self.compiled_path / "setup.py"
        if not setup_py_file.exists():
            setup_py_file.write_text(
                """
from setuptools import setup

setup()
""",
                encoding="utf-8",
            )

        if modified:
            pyproject_file.write_text(content, encoding="utf-8")
            console.print("  ✅ 更新pyproject.toml配置 (公开模式)", style="green")
        else:
            console.print("  ✓ pyproject.toml配置已满足要求", style="dim")

    def _verify_wheel_contents(self, wheel_file: Path) -> None:
        console.print("  🔍 验证wheel包内容...", style="cyan")
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with zipfile.ZipFile(wheel_file, "r") as zip_ref:
                zip_ref.extractall(temp_path)
                all_files = list(zip_ref.namelist())
            pyc_count = sum(1 for f in all_files if f.endswith(".pyc"))
            py_count = sum(1 for f in all_files if f.endswith(".py"))
            binary_count = sum(1 for f in all_files if f.endswith((".so", ".pyd", ".dylib")))
            total_count = len(all_files)
            console.print(
                f"    📊 文件总数: {total_count} (.pyc: {pyc_count}, .py: {py_count}, binary: {binary_count})"
            )

            if self.mode == "private":
                # Private mode: expect .pyc files
                if pyc_count == 0 and binary_count == 0:
                    console.print("    ❌ 错误: wheel中没有.pyc或二进制扩展文件", style="red")
                    sample = all_files[:10]
                    for f in sample:
                        console.print(f"       - {f}")
            else:
                # Public mode: expect .py files
                if py_count == 0:
                    console.print("    ⚠️ 警告: wheel中没有.py源文件", style="yellow")
                    sample = all_files[:10]
                    for f in sample:
                        console.print(f"       - {f}")
                else:
                    console.print(f"    ✅ 源码包含 {py_count} 个.py文件", style="green")

    def _auto_push_to_github(self) -> None:
        """Auto-push to GitHub after successful PyPI upload if in git repo."""
        # Check if we're in a git repository
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                cwd=self.package_path,
            )
            if result.returncode != 0:
                return  # Not a git repo, skip
        except FileNotFoundError:
            return  # Git not installed

        # Check if there are commits to push
        try:
            result = subprocess.run(
                ["git", "log", "@{u}..", "--oneline"],
                capture_output=True,
                text=True,
                cwd=self.package_path,
            )
            if not result.stdout.strip():
                return  # No commits to push
        except Exception:  # noqa: BLE001
            return  # Can't determine, skip

        console.print("\n🚀 Pushing version commit...", style="cyan")

        # Set environment variable to tell pre-push hook to skip processing
        env = os.environ.copy()
        env["SAGE_PYPI_PUBLISHER_PUSHING"] = "1"

        try:
            result = subprocess.run(
                ["git", "push", "--no-verify"],  # Skip pre-push hook to avoid recursion
                capture_output=True,
                text=True,
                cwd=self.package_path,
                env=env,
            )
            if result.returncode == 0:
                # Parse output to show summary
                output = result.stdout + result.stderr
                console.print(output, style="dim")
                console.print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                console.print("✅ [green bold]Push completed successfully![/green bold]")
                console.print("   Version bumped and uploaded to PyPI")
                console.print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            else:
                error_output = result.stderr.strip() if result.stderr else "Unknown error"
                console.print(f"⚠️  Git push failed: {error_output}", style="yellow")
                console.print("💡 Please run 'git push' manually", style="dim")
        except Exception as e:  # noqa: BLE001
            console.print(f"⚠️  Could not auto-push: {e}", style="yellow")
            console.print("💡 Please run 'git push' manually", style="dim")


def compile_multiple_packages(
    package_paths: Iterable[Path],
    output_dir: Path | None = None,
    build_wheels: bool = False,
    mode: BuildMode = "private",
) -> dict[str, bool]:
    packages = list(package_paths)
    results: dict[str, bool] = {}
    mode_name = "保密模式" if mode in ("private", "bytecode") else "公开模式"
    console.print(f"🎯 批量编译 {len(packages)} 个包 ({mode_name})", style="bold cyan")
    for package_path in packages:
        console.print(f"\n处理包: {package_path.name}", style="bold")
        try:
            compiler = BytecodeCompiler(package_path, mode=mode)
            compiled = compiler.compile_package(output_dir)
            if build_wheels:
                compiler.build_wheel(compiled)
            results[package_path.name] = True
        except Exception as e:  # noqa: BLE001
            console.print(f"❌ 处理失败: {e}", style="red")
            results[package_path.name] = False
    return results
