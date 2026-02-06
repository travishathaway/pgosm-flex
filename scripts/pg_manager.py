#!/usr/bin/env python3
"""
Cross-platform PostgreSQL management script for pgosm-flex development.

Provides commands to start, stop, destroy, and check status of a local PostgreSQL
instance running on port 65432 (to avoid conflicts with system PostgreSQL).

Usage:
    python scripts/pg_manager.py start     # Initialize and start PostgreSQL
    python scripts/pg_manager.py stop      # Stop PostgreSQL (preserve data)
    python scripts/pg_manager.py destroy   # Stop and remove all data
    python scripts/pg_manager.py status    # Check PostgreSQL status
    python scripts/pg_manager.py shell     # Open interactive PostgreSQL shell

The script uses the pgosm_flex.postgres library for core PostgreSQL operations.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from pgosm_flex.postgres import Platform, PostgresCluster

# Constants
DEFAULT_PORT = int(os.environ.get("PGOSM_PG_PORT", "65432"))
DEFAULT_USER = "postgres"
DEFAULT_DB = "pgosm"


class Colors:
    """ANSI color codes (only if terminal supports color)"""
    GREEN = '\033[92m' if sys.stdout.isatty() else ''
    RED = '\033[91m' if sys.stdout.isatty() else ''
    YELLOW = '\033[93m' if sys.stdout.isatty() else ''
    BLUE = '\033[94m' if sys.stdout.isatty() else ''
    RESET = '\033[0m' if sys.stdout.isatty() else ''


def print_success(msg: str) -> None:
    """Print success message with green checkmark."""
    print(f"{Colors.GREEN}✓{Colors.RESET} {msg}")


def print_error(msg: str) -> None:
    """Print error message with red X to stderr."""
    print(f"{Colors.RED}✗{Colors.RESET} {msg}", file=sys.stderr)


def print_info(msg: str) -> None:
    """Print informational message with indentation."""
    print(f"  {msg}")


def print_warning(msg: str) -> None:
    """Print warning message with yellow warning symbol."""
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {msg}")


def cmd_start(args: argparse.Namespace) -> int:
    """
    Start PostgreSQL with auto-initialization and database setup.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    data_dir = Path.cwd() / ".pgdata"
    cluster = PostgresCluster(data_dir, args.port, DEFAULT_USER)

    # 1. Check if already running
    if cluster.is_running():
        print_error("PostgreSQL is already running")
        print_info("Use 'pixi run pg:stop' to stop it first")
        return 1

    # 2. Initialize if needed
    if not cluster.data_mgr.exists():
        print_info("Initializing PostgreSQL cluster...")
        cluster.pg_mgr.initialize()
        print_success(f"PostgreSQL cluster initialized at {cluster.data_mgr.data_dir}")

    # 3. Start server
    print_info("Starting PostgreSQL...")
    cluster.pg_mgr.start()

    # 4. Wait for ready
    if not cluster.pg_mgr.wait_for_ready(timeout=30):
        print_error("PostgreSQL failed to start")
        print_info(f"Check log file: {cluster.data_mgr.logfile}")
        return 1

    print_success("PostgreSQL started")

    # 5. Create database if needed
    if not cluster.pg_mgr.database_exists(DEFAULT_DB):
        print_info(f"Creating {DEFAULT_DB} database...")
        cluster.pg_mgr.create_database(DEFAULT_DB)
        print_success(f"Database {DEFAULT_DB} created")

    # 6. Enable PostGIS
    print_info("Enabling PostGIS extension...")
    try:
        cluster.pg_mgr.enable_postgis(DEFAULT_DB)
        print_success("PostGIS extension enabled")
    except RuntimeError as e:
        print_warning("Failed to enable PostGIS extension")
        print_info(str(e))
        print_info("You may need to install PostGIS for your PostgreSQL installation")

    # 7. Success message with connection info
    print()
    print_success("PostgreSQL is ready")
    print_info(f"Connection: {cluster.connection_string(DEFAULT_DB)}")
    print_info(f"Log file: {cluster.data_mgr.logfile}")

    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    """
    Stop PostgreSQL gracefully.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    data_dir = Path.cwd() / ".pgdata"
    cluster = PostgresCluster(data_dir, args.port, DEFAULT_USER)

    if not cluster.data_mgr.exists():
        print_info("PostgreSQL data directory not found")
        return 0

    if not cluster.is_running():
        print_info("PostgreSQL is not running")
        return 0

    print_info("Stopping PostgreSQL...")
    cluster.pg_mgr.stop()
    print_success(f"PostgreSQL stopped (data preserved in {cluster.data_mgr.data_dir})")

    return 0


def cmd_destroy(args: argparse.Namespace) -> int:
    """
    Stop PostgreSQL and remove data directory.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    data_dir = Path.cwd() / ".pgdata"
    cluster = PostgresCluster(data_dir, args.port, DEFAULT_USER)

    # Stop if running
    if cluster.is_running():
        print_info("Stopping PostgreSQL...")
        try:
            cluster.pg_mgr.stop()
            print_success("PostgreSQL stopped")
        except RuntimeError as e:
            print_warning(f"Failed to stop PostgreSQL cleanly: {e}")
            print_info("Continuing with data directory removal...")

    if not cluster.data_mgr.exists():
        print_info("No .pgdata directory found")
        return 0

    # Confirm deletion (unless --force)
    if not args.force:
        print_warning(f"This will permanently delete {cluster.data_mgr.data_dir}")
        response = input("Continue? [y/N]: ").strip().lower()
        if response not in ('y', 'yes'):
            print_info("Cancelled")
            return 0

    print_info("Removing .pgdata directory...")
    shutil.rmtree(cluster.data_mgr.data_dir)
    print_success("PostgreSQL data directory destroyed")

    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """
    Report PostgreSQL status.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    data_dir = Path.cwd() / ".pgdata"
    cluster = PostgresCluster(data_dir, args.port, DEFAULT_USER)

    if not cluster.data_mgr.exists():
        print(f"{Colors.BLUE}Status:{Colors.RESET} Data directory not initialized")
        print_info("Run: pixi run pg:start")
        return 0

    if not cluster.is_running():
        print(f"{Colors.BLUE}Status:{Colors.RESET} Stopped (data directory exists)")
        print_info("Run: pixi run pg:start")
        return 0

    # Running - gather details
    print(f"{Colors.GREEN}Status:{Colors.RESET} Running")

    # Read PID from postmaster.pid
    try:
        pid = cluster.data_mgr.postmaster_pid.read_text().split('\n')[0].strip()
        print(f"PID: {pid}")
    except (OSError, IndexError):
        pass

    # Show connection info
    print(f"Port: {args.port}")
    print(f"Connection: {cluster.connection_string(DEFAULT_DB)}")
    print(f"Data directory: {cluster.data_mgr.data_dir}")
    print(f"Log file: {cluster.data_mgr.logfile}")

    return 0


def cmd_shell(args: argparse.Namespace) -> int:
    """
    Launch interactive PostgreSQL shell (psql) connected to pgosm database.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code from psql (0 for success, non-zero for error)
    """
    data_dir = Path.cwd() / ".pgdata"
    cluster = PostgresCluster(data_dir, args.port, DEFAULT_USER)

    # Check if PostgreSQL is running
    if not cluster.data_mgr.exists():
        print_error("PostgreSQL data directory not found")
        print_info("Run: pixi run pg:start")
        return 1

    if not cluster.is_running():
        print_error("PostgreSQL is not running")
        print_info("Run: pixi run pg:start")
        return 1

    # Find psql command
    psql_cmd = Platform.find_pg_command("psql")

    # Launch psql interactively (don't capture output, let it use the terminal)
    print_info(f"Connecting to {DEFAULT_DB} database on port {args.port}...")

    try:
        result = subprocess.run(
            [
                psql_cmd,
                "-h", "localhost",
                "-p", str(args.port),
                "-U", DEFAULT_USER,
                "-d", DEFAULT_DB
            ],
            # Don't capture output - let psql use stdin/stdout/stderr directly
            capture_output=False,
            text=True
        )
        return result.returncode
    except KeyboardInterrupt:
        # User exited psql with Ctrl+C - this is normal
        print()  # New line after ^C
        return 0


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = argparse.ArgumentParser(
        description="Manage local PostgreSQL instance for pgosm-flex development",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/pg_manager.py start              # Start PostgreSQL on default port (65432)
  python scripts/pg_manager.py --port 54321 start # Start on custom port
  python scripts/pg_manager.py status             # Check status
  python scripts/pg_manager.py stop               # Stop (preserve data)
  python scripts/pg_manager.py destroy            # Stop and remove data (interactive)
  python scripts/pg_manager.py destroy --force    # Stop and remove data (no confirmation)

Environment variables:
  PGOSM_PG_PORT    PostgreSQL port (default: 65432)
        """
    )

    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"PostgreSQL port (default: {DEFAULT_PORT})"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # start command
    subparsers.add_parser(
        "start",
        help="Initialize (if needed) and start PostgreSQL"
    )

    # stop command
    subparsers.add_parser(
        "stop",
        help="Stop PostgreSQL gracefully (preserve data)"
    )

    # destroy command
    destroy_parser = subparsers.add_parser(
        "destroy",
        help="Stop PostgreSQL and remove all data"
    )
    destroy_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt"
    )

    # status command
    subparsers.add_parser(
        "status",
        help="Show PostgreSQL status and connection info"
    )

    # shell command
    subparsers.add_parser(
        "shell",
        help="Open interactive PostgreSQL shell (psql)"
    )

    args = parser.parse_args()

    # Route to command handler
    handlers = {
        "start": cmd_start,
        "stop": cmd_stop,
        "destroy": cmd_destroy,
        "status": cmd_status,
        "shell": cmd_shell,
    }

    try:
        return handlers[args.command](args)
    except FileNotFoundError as e:
        print_error(f"PostgreSQL not found: {e}")
        print_info("Install PostgreSQL with `pixi add postgresql` and ensure it's in your PATH")

        return 2
    except RuntimeError as e:
        print_error(str(e))
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
