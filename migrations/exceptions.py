"""
Custom exceptions for the migration system.
"""


class MigrationError(Exception):
    """Base exception for migration errors."""

    def __init__(self, message: str, migration_id: str = None):
        super().__init__(message)
        self.migration_id = migration_id


class MigrationNotFoundError(MigrationError):
    """Raised when a migration is not found."""

    pass


class MigrationAlreadyAppliedError(MigrationError):
    """Raised when trying to apply an already applied migration."""

    pass


class MigrationNotAppliedError(MigrationError):
    """Raised when trying to rollback a migration that was never applied."""

    pass


class MigrationChecksumError(MigrationError):
    """Raised when a migration file has been modified after being applied."""

    pass


class MigrationExecutionError(MigrationError):
    """Raised when a migration fails during execution."""

    pass


class MigrationLockError(MigrationError):
    """Raised when cannot acquire migration lock."""

    pass
