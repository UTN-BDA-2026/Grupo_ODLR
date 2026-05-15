"""
Migration versions directory.

Place your migration files here. They will be executed in alphabetical order.

Migration file naming convention:
    YYYYMMDD_HHMMSS_description.py

Example:
    20240115_100000_create_indexes.py
    20240115_103000_add_status_field.py

Each migration must define:
    - migration_id: Unique identifier (should match filename)
    - description: Human-readable description
    - up(db): Async function to apply the migration
    - down(db): Async function to rollback the migration
"""
