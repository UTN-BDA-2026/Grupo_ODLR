"""
Command-line interface for the migration system.

Provides commands to manage MongoDB migrations.
"""

import argparse
import asyncio
import sys
from typing import List, Optional

from migrations.runner import MigrationRunner


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        prog="migrations",
        description="MongoDB Migration System for PDF Extract API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m migrations status              # Show current status
  python -m migrations migrate             # Run all pending migrations
  python -m migrations migrate --dry-run   # Preview migrations
  python -m migrations rollback            # Rollback last migration
  python -m migrations rollback --steps 3  # Rollback 3 migrations
  python -m migrations create "add field"  # Create new migration
  python -m migrations verify              # Verify migration integrity
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # status command
    status_parser = subparsers.add_parser(
        "status", help="Show current migration status"
    )

    # migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Execute pending migrations")
    migrate_parser.add_argument(
        "--target", type=str, help="Stop at specific migration ID"
    )
    migrate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without running",
    )

    # rollback command
    rollback_parser = subparsers.add_parser("rollback", help="Rollback migrations")
    rollback_group = rollback_parser.add_mutually_exclusive_group()
    rollback_group.add_argument(
        "--target", type=str, help="Rollback to specific migration ID"
    )
    rollback_group.add_argument(
        "--steps",
        type=int,
        default=1,
        help="Number of migrations to rollback (default: 1)",
    )
    rollback_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without running",
    )

    # create command
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument(
        "description", nargs="+", help="Description of the migration"
    )

    # verify command
    verify_parser = subparsers.add_parser("verify", help="Verify migration integrity")

    return parser


async def handle_status(runner: MigrationRunner):
    """Handle status command."""
    status = await runner.status()

    print("\n" + "=" * 60)
    print("MIGRATION STATUS")
    print("=" * 60)
    print(f"Total migrations:   {status['total_migrations']}")
    print(f"Applied:            {status['applied_count']}")
    print(f"Pending:            {status['pending_count']}")

    if status["last_applied"]:
        print(f"\nLast applied:       {status['last_applied']}")
        print(f"Applied at:         {status['last_applied_at']}")

    if status["pending"]:
        print(f"\nPending migrations:")
        for mid in status["pending"]:
            print(f"  - {mid}")
    else:
        print("\n✓ All migrations are up to date")

    print("=" * 60 + "\n")


async def handle_migrate(runner: MigrationRunner, args):
    """Handle migrate command."""
    try:
        await runner.migrate(target=args.target, dry_run=args.dry_run)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_rollback(runner: MigrationRunner, args):
    """Handle rollback command."""
    try:
        await runner.rollback(
            target=args.target, steps=args.steps, dry_run=args.dry_run
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_create(runner: MigrationRunner, args):
    """Handle create command."""
    description = " ".join(args.description)
    migration_id = await runner.create(description)
    print(f"\n✓ Created migration: {migration_id}")
    print(f"  Edit the file to implement your migration\n")


async def handle_verify(runner: MigrationRunner):
    """Handle verify command."""
    issues = await runner.verify()

    print("\n" + "=" * 60)
    print("MIGRATION VERIFICATION")
    print("=" * 60)

    if not issues:
        print("✓ All migrations verified successfully")
    else:
        print(f"✗ Found {len(issues)} issue(s):")
        for issue in issues:
            print(f"  - [{issue['issue']}] {issue['migration_id']}: {issue['message']}")

    print("=" * 60 + "\n")


async def main(args: Optional[List[str]] = None):
    """Main entry point for CLI."""
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    if not parsed_args.command:
        parser.print_help()
        sys.exit(0)

    runner = MigrationRunner()

    try:
        if parsed_args.command == "status":
            await handle_status(runner)
        elif parsed_args.command == "migrate":
            await handle_migrate(runner, parsed_args)
        elif parsed_args.command == "rollback":
            await handle_rollback(runner, parsed_args)
        elif parsed_args.command == "create":
            await handle_create(runner, parsed_args)
        elif parsed_args.command == "verify":
            await handle_verify(runner)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    asyncio.run(main())
