"""
Manylinux wheel builder for packages with C/C++ extensions.

Handles platform tag modifications for packages that can't use auditwheel
(e.g., packages with external dependencies like MKL, FAISS, CUDA).
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from rich.console import Console

from pypi_publisher.exceptions import BuildError

console = Console()


class ManylinuxBuilder:
    """Build manylinux wheels for C/C++ extension packages."""

    def __init__(self, package_path: Path):
        self.package_path = Path(package_path)
        if not self.package_path.exists():
            raise BuildError(f"Package path does not exist: {package_path}")
        if not (self.package_path / "pyproject.toml").exists():
            raise BuildError(f"No pyproject.toml found in: {package_path}")

    def build_manylinux_wheel(
        self,
        output_dir: Path | None = None,
        platform_tag: str = "manylinux_2_34_x86_64",
        python_tag: str | None = None,
    ) -> Path:
        """
        Build a wheel with manylinux platform tags.

        Args:
            output_dir: Where to place the final wheel (default: ./wheelhouse)
            platform_tag: The manylinux platform tag to use
            python_tag: Python implementation tag (auto-detected if None)

        Returns:
            Path to the created manylinux wheel
        """
        console.print("🔧 Building wheel with manylinux tags...", style="cyan")

        # Clean previous builds
        dist_dir = self.package_path / "dist"
        if dist_dir.exists():
            import shutil
            shutil.rmtree(dist_dir)

        # Build the wheel
        console.print("  📦 Building wheel...")
        result = subprocess.run(
            [sys.executable, "-m", "build", "--wheel"],
            cwd=self.package_path,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise BuildError(f"Wheel build failed: {result.stderr}")

        # Find the built wheel
        wheels = list(dist_dir.glob("*.whl"))
        if not wheels:
            raise BuildError("No wheel file found after build")

        wheel_file = wheels[0]
        console.print(f"  ✓ Built: {wheel_file.name}")

        # Modify the wheel to add manylinux tags
        console.print("  🏷️  Updating wheel platform tags...")
        manylinux_wheel = self._modify_wheel_tags(
            wheel_file,
            platform_tag=platform_tag,
            python_tag=python_tag,
        )

        # Move to output directory
        if output_dir:
            output_dir = Path(output_dir)
        else:
            output_dir = self.package_path / "wheelhouse"

        output_dir.mkdir(parents=True, exist_ok=True)

        final_path = output_dir / manylinux_wheel.name
        if final_path.exists():
            final_path.unlink()

        import shutil
        shutil.move(str(manylinux_wheel), str(final_path))

        console.print(f"✅ Created manylinux wheel: {final_path.name}", style="green")
        console.print(f"   Location: {final_path}")
        return final_path

    def _modify_wheel_tags(
        self,
        wheel_file: Path,
        platform_tag: str,
        python_tag: str | None = None,
    ) -> Path:
        """Modify wheel metadata to use manylinux tags."""
        import re

        # Auto-detect python tag if not provided
        if python_tag is None:
            version_info = sys.version_info
            python_tag = f"cp{version_info.major}{version_info.minor}"

        # Create temp directory for wheel modification
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Unpack the wheel
            temp_path / "unpacked"
            console.print("  📂 Unpacking wheel...")
            subprocess.run(
                [sys.executable, "-m", "wheel", "unpack", str(wheel_file), "-d", str(temp_path)],
                check=True,
                capture_output=True,
            )

            # Find the unpacked directory
            unpacked = next(temp_path.glob("*"))

            # Find and modify WHEEL file
            wheel_info_file = next(unpacked.glob("*.dist-info/WHEEL"))
            console.print("  ✏️  Modifying WHEEL metadata...")

            content = wheel_info_file.read_text(encoding="utf-8")

            # Replace platform tags
            # Handle various tag formats: cpXXX-cpXXX-platform, cpXXX-abiX-platform
            tag_pattern = r"Tag: (cp\d+)-(cp\d+|abi\d+)-(linux_\w+|win_\w+|macosx_\w+)"
            new_tag = f"Tag: {python_tag}-{python_tag}-{platform_tag}"

            modified_content = re.sub(tag_pattern, new_tag, content)
            wheel_info_file.write_text(modified_content, encoding="utf-8")

            console.print(f"     Updated tag to: {new_tag}")

            # Repack the wheel
            console.print("  📦 Repacking wheel...")
            subprocess.run(
                [sys.executable, "-m", "wheel", "pack", str(unpacked), "-d", str(temp_path)],
                check=True,
                capture_output=True,
                text=True,
            )

            # Find the repacked wheel and rename with correct filename
            repacked_wheels = list(temp_path.glob("*.whl"))
            if not repacked_wheels:
                raise BuildError("Failed to repack wheel")

            repacked_wheel = repacked_wheels[0]

            # Create the correct filename
            name_match = re.match(r"^(.+?)-(\d+(\.\d+)+)", wheel_file.name)
            if name_match:
                pkg_name = name_match.group(1)
                version = name_match.group(2)
                new_filename = f"{pkg_name}-{version}-{python_tag}-{python_tag}-{platform_tag}.whl"
            else:
                # Fallback: just replace the platform in original name
                new_filename = re.sub(
                    r"-(cp\d+)-(cp\d+|abi\d+)-(linux_\w+|win_\w+|macosx_\w+)\.whl$",
                    f"-{python_tag}-{python_tag}-{platform_tag}.whl",
                    wheel_file.name,
                )

            # Move to a persistent location before temp_dir is cleaned up
            import shutil
            final_wheel = wheel_file.parent / new_filename
            shutil.copy(str(repacked_wheel), str(final_wheel))

            return final_wheel
