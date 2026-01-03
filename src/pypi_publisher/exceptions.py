"""
PyPI Publisher exceptions.

This module defines the exception hierarchy for PyPI Publisher.
All toolkit-specific exceptions inherit from PyPIPublisherError.
"""


class PyPIPublisherError(Exception):
    """Base exception for all PyPI Publisher errors."""

    def __init__(
        self,
        message: str,
        details: dict | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause

    def __str__(self) -> str:
        parts = [self.message]
        if self.details:
            parts.append(f"Details: {self.details}")
        if self.cause:
            parts.append(f"Caused by: {self.cause}")
        return " | ".join(parts)


class CompilationError(PyPIPublisherError):
    """Raised when bytecode compilation fails."""

    def __init__(
        self,
        message: str,
        source_file: str | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.source_file = source_file


class BuildError(PyPIPublisherError):
    """Raised when wheel building fails."""

    def __init__(
        self,
        message: str,
        package_name: str | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.package_name = package_name


class UploadError(PyPIPublisherError):
    """Raised when PyPI upload fails."""

    def __init__(
        self,
        message: str,
        repository: str | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.repository = repository


class ConfigError(PyPIPublisherError):
    """Raised when there are configuration-related errors."""

    def __init__(self, message: str, config_path: str | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.config_path = config_path
