"""
Custom exceptions.

Defines application-specific exceptions for better error handling.
Follows the Open/Closed Principle for extensibility.
"""

from typing import Any, Dict, Optional


class ApplicationException(Exception):
    """
    Base application exception.

    All custom exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(ApplicationException):
    """Exception for validation errors."""

    def __init__(
        self,
        message: str = "Validation error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, status_code=422, details=details)


class NotFoundException(ApplicationException):
    """Exception for resource not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ConflictException(ApplicationException):
    """Exception for resource conflicts."""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, status_code=409)


class UnauthorizedException(ApplicationException):
    """Exception for unauthorized access."""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)


class ForbiddenException(ApplicationException):
    """Exception for forbidden access."""

    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403)
