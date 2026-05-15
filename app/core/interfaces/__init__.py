"""
Core interfaces module.

Defines abstract interfaces for dependency inversion.
Follows the Interface Segregation Principle (ISP).
"""

from app.core.interfaces.database import DatabaseInterface
from app.core.interfaces.repository import RepositoryInterface

__all__ = ["DatabaseInterface", "RepositoryInterface"]
