"""Logging interfaces following DIP.

Defines the contract that logging implementations must satisfy.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class LoggerInterface(Protocol):
    """Protocol defining the logging interface.

    DIP: Domain code depends on this abstraction, not concrete loggers.
    ISP: Minimal interface with only what clients need.

    Any logger implementation must satisfy this protocol.
    """

    def debug(self, msg: str, *args, **kwargs) -> None:
        """Log debug message."""
        ...

    def info(self, msg: str, *args, **kwargs) -> None:
        """Log info message."""
        ...

    def warning(self, msg: str, *args, **kwargs) -> None:
        """Log warning message."""
        ...

    def error(self, msg: str, *args, **kwargs) -> None:
        """Log error message."""
        ...

    def critical(self, msg: str, *args, **kwargs) -> None:
        """Log critical message."""
        ...
