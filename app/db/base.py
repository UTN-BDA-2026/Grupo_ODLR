"""
Base model for SQLAlchemy.

Provides the declarative base for all models.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    Provides common functionality for all database models.
    """

    pass
