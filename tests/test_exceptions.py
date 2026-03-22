from __future__ import annotations

from wheelwright.exceptions import BuildError, CompilationError, PyPIPublisherError, UploadError


def test_base_exception_string_contains_message_details_and_cause() -> None:
    error = PyPIPublisherError(
        "build failed",
        details={"step": "wheel"},
        cause=RuntimeError("boom"),
    )

    text = str(error)
    assert "build failed" in text
    assert "step" in text
    assert "boom" in text


def test_specialized_exceptions_keep_context_fields() -> None:
    compile_error = CompilationError("compile failed", source_file="foo.py")
    build_error = BuildError("build failed", package_name="demo")
    upload_error = UploadError("upload failed", repository="testpypi")

    assert compile_error.source_file == "foo.py"
    assert build_error.package_name == "demo"
    assert upload_error.repository == "testpypi"
