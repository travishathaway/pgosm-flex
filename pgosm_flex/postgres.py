"""
PostgreSQL management library for pgosm-flex.

Provides reusable classes for managing PostgreSQL instances, suitable for both
CLI tools and pytest fixtures. Handles initialization, lifecycle management,
database operations, and cleanup.
"""

import os
import platform
import shutil
import subprocess
import time
from pathlib import Path


class Platform:
    """Handle platform-specific differences."""

    @staticmethod
    def is_windows() -> bool:
        """Check if running on Windows."""
        return platform.system() == "Windows"

    @staticmethod
    def find_pg_command(cmd: str) -> str:
        """
        Find PostgreSQL command, handling platform differences.

        Args:
            cmd: Command name (e.g., 'initdb', 'pg_ctl')

        Returns
        -------
            Full path to command

        Raises
        ------
            FileNotFoundError: If command not found in PATH or common locations
        """
        if Platform.is_windows():
            cmd = f"{cmd}.exe"

        # Try PATH first
        found = shutil.which(cmd)
        if found:
            return found

        # Windows fallback: Check common PostgreSQL install locations
        if Platform.is_windows():
            prog_files = os.environ.get("PROGRAMFILES", "C:/Program Files")
            pg_path = Path(prog_files) / "PostgreSQL"

            if pg_path.exists():
                # Find latest version directory (e.g., PostgreSQL/16/bin)
                versions = sorted([d for d in pg_path.iterdir() if d.is_dir()])
                if versions:
                    latest_bin = versions[-1] / "bin" / cmd
                    if latest_bin.exists():
                        return str(latest_bin)

        raise FileNotFoundError(
            f"PostgreSQL command '{cmd}' not found in PATH. "
            "Install PostgreSQL and ensure it's in your PATH."
        )


class PgDataManager:
    """Manage PostgreSQL data directory and check running status."""

    def __init__(self, data_dir: Path):
        """
        Initialize data directory manager.

        Args:
            data_dir: PostgreSQL data directory path
        """
        self._data_dir = data_dir

    @property
    def data_dir(self) -> Path:
        """Get path to PostgreSQL data directory."""
        return self._data_dir

    @property
    def logfile(self) -> Path:
        """Get path to PostgreSQL log file."""
        return self._data_dir / "logfile"

    @property
    def postmaster_pid(self) -> Path:
        """Get path to PostgreSQL PID file."""
        return self._data_dir / "postmaster.pid"

    def exists(self) -> bool:
        """Check if data directory exists."""
        return self._data_dir.exists() and self._data_dir.is_dir()

    def is_running(self) -> bool:
        """
        Check if PostgreSQL is running.

        Handles stale PID files by checking if the process actually exists.

        Returns
        -------
            True if PostgreSQL is running, False otherwise
        """
        if not self.postmaster_pid.exists():
            return False

        try:
            # Read PID from first line of postmaster.pid
            pid_text = self.postmaster_pid.read_text().strip()
            if not pid_text:
                return False

            pid = int(pid_text.split("\n")[0])

            # Check if process exists (cross-platform)
            if Platform.is_windows():
                # Windows: use tasklist command
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True, timeout=5
                )
                return str(pid) in result.stdout
            # Unix: send signal 0 (doesn't kill, just checks existence)
            os.kill(pid, 0)
            return True
        except (ValueError, ProcessLookupError, OSError, subprocess.TimeoutExpired):
            # PID file invalid or process doesn't exist - stale file
            return False


class PostgresManager:
    """Core PostgreSQL operations using subprocess."""

    def __init__(self, data_mgr: PgDataManager, port: int, user: str = "postgres"):
        """
        Initialize PostgreSQL manager.

        Args:
            data_mgr: Data directory manager
            port: PostgreSQL port number
            user: PostgreSQL user name (default: postgres)
        """
        self.data_mgr = data_mgr
        self.port = port
        self.user = user

    def _run_command(
        self, cmd: list[str], capture_output: bool = True, check: bool = True, timeout: int = 30
    ) -> subprocess.CompletedProcess:
        """
        Run command with error handling.

        Args:
            cmd: Command and arguments
            capture_output: Whether to capture stdout/stderr
            check: Whether to raise exception on non-zero exit
            timeout: Command timeout in seconds

        Returns
        -------
            CompletedProcess instance

        Raises
        ------
            RuntimeError: If command fails or times out
        """
        try:
            result = subprocess.run(
                cmd, capture_output=capture_output, text=True, check=check, timeout=timeout
            )
            return result
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Command timed out after {timeout}s: {' '.join(cmd)}")
        except subprocess.CalledProcessError as e:
            error_msg = f"Command failed: {' '.join(cmd)}"
            if e.stderr:
                error_msg += f"\n{e.stderr}"
            raise RuntimeError(error_msg)

    def initialize(self) -> None:
        """
        Initialize PostgreSQL data directory using initdb.

        Raises
        ------
            RuntimeError: If initialization fails
        """
        initdb_cmd = Platform.find_pg_command("initdb")

        cmd = [
            initdb_cmd,
            "-D",
            str(self.data_mgr.data_dir),
            "-U",
            self.user,
            "--no-locale",
            "--encoding=UTF8",
        ]

        self._run_command(cmd)

    def start(self) -> None:
        """
        Start PostgreSQL server using pg_ctl.

        Raises
        ------
            RuntimeError: If start fails
        """
        pg_ctl_cmd = Platform.find_pg_command("pg_ctl")

        cmd = [
            pg_ctl_cmd,
            "-D",
            str(self.data_mgr.data_dir),
            "-l",
            str(self.data_mgr.logfile),
            "-o",
            f"-p {self.port}",
            "start",
        ]

        self._run_command(cmd)

    def stop(self) -> None:
        """
        Stop PostgreSQL server gracefully using pg_ctl.

        Raises
        ------
            RuntimeError: If stop fails
        """
        pg_ctl_cmd = Platform.find_pg_command("pg_ctl")

        cmd = [pg_ctl_cmd, "-D", str(self.data_mgr.data_dir), "stop", "-m", "fast"]

        self._run_command(cmd, timeout=60)

    def wait_for_ready(self, timeout: int = 30, verbose: bool = True) -> bool:
        """
        Wait for PostgreSQL to be ready to accept connections.

        Args:
            timeout: Maximum seconds to wait
            verbose: Whether to print progress messages

        Returns
        -------
            True if PostgreSQL became ready, False if timeout
        """
        pg_isready_cmd = Platform.find_pg_command("pg_isready")

        start_time = time.time()
        last_dot_time = start_time

        if verbose:
            print("  Waiting for PostgreSQL to be ready")

        while time.time() - start_time < timeout:
            # Add a dot every second for visual feedback
            if verbose:
                current_time = time.time()
                if current_time - last_dot_time >= 1.0:
                    print(".", end="", flush=True)
                    last_dot_time = current_time

            try:
                result = subprocess.run(
                    [pg_isready_cmd, "-h", "localhost", "-p", str(self.port)],
                    capture_output=True,
                    timeout=2,
                )
                if result.returncode == 0:
                    if verbose:
                        print()  # New line after dots
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

            time.sleep(0.5)

        if verbose:
            print()  # New line after dots
        return False

    def database_exists(self, dbname: str) -> bool:
        """
        Check if database exists.

        Args:
            dbname: Database name to check

        Returns
        -------
            True if database exists, False otherwise
        """
        psql_cmd = Platform.find_pg_command("psql")

        cmd = [
            psql_cmd,
            "-h",
            "localhost",
            "-p",
            str(self.port),
            "-U",
            self.user,
            "-d",
            "postgres",
            "-tAc",
            f"SELECT 1 FROM pg_database WHERE datname='{dbname}'",
        ]

        try:
            result = self._run_command(cmd, check=False)
            return result.stdout.strip() == "1"
        except RuntimeError:
            return False

    def create_database(self, dbname: str) -> None:
        """
        Create database.

        Args:
            dbname: Database name to create

        Raises
        ------
            RuntimeError: If database creation fails
        """
        psql_cmd = Platform.find_pg_command("psql")

        cmd = [
            psql_cmd,
            "-h",
            "localhost",
            "-p",
            str(self.port),
            "-U",
            self.user,
            "-d",
            "postgres",
            "-c",
            f"CREATE DATABASE {dbname}",
        ]

        self._run_command(cmd)

    def drop_database(self, dbname: str) -> None:
        """
        Drop database.

        Args:
            dbname: Database name to drop

        Raises
        ------
            RuntimeError: If database drop fails
        """
        psql_cmd = Platform.find_pg_command("psql")

        cmd = [
            psql_cmd,
            "-h",
            "localhost",
            "-p",
            str(self.port),
            "-U",
            self.user,
            "-d",
            "postgres",
            "-c",
            f"DROP DATABASE IF EXISTS {dbname}",
        ]

        self._run_command(cmd)

    def enable_postgis(self, dbname: str) -> None:
        """
        Enable PostGIS extension in database.

        Args:
            dbname: Database name

        Raises
        ------
            RuntimeError: If PostGIS extension creation fails
        """
        psql_cmd = Platform.find_pg_command("psql")

        cmd = [
            psql_cmd,
            "-h",
            "localhost",
            "-p",
            str(self.port),
            "-U",
            self.user,
            "-d",
            dbname,
            "-c",
            "CREATE EXTENSION IF NOT EXISTS postgis",
        ]

        self._run_command(cmd)


class PostgresCluster:
    """High-level PostgreSQL cluster management interface."""

    def __init__(self, data_dir: Path, port: int, user: str = "postgres"):
        """
        Initialize PostgreSQL cluster manager.

        Args:
            data_dir: PostgreSQL data directory path
            port: PostgreSQL port number
            user: PostgreSQL user name (default: postgres)
        """
        self.data_mgr = PgDataManager(data_dir)
        self.pg_mgr = PostgresManager(self.data_mgr, port, user)
        self.port = port
        self.user = user

    def setup(self, databases: list[str] | None = None, enable_postgis: bool = False) -> None:
        """
        Initialize, start PostgreSQL, and create databases.

        Args:
            databases: List of database names to create (optional)
            enable_postgis: Whether to enable PostGIS extension in created databases

        Raises
        ------
            RuntimeError: If setup fails
        """
        # Initialize if needed
        if not self.data_mgr.exists():
            self.pg_mgr.initialize()

        # Start if not running
        if not self.data_mgr.is_running():
            self.pg_mgr.start()

        # Wait for ready
        if not self.pg_mgr.wait_for_ready(timeout=30, verbose=False):
            raise RuntimeError("PostgreSQL failed to start")

        # Create databases if specified
        if databases:
            for dbname in databases:
                if not self.pg_mgr.database_exists(dbname):
                    self.pg_mgr.create_database(dbname)

                if enable_postgis:
                    self.pg_mgr.enable_postgis(dbname)

    def teardown(self, remove_data: bool = False) -> None:
        """
        Stop PostgreSQL and optionally remove data directory.

        Args:
            remove_data: Whether to remove data directory after stopping
        """
        if self.data_mgr.is_running():
            self.pg_mgr.stop()

        if remove_data and self.data_mgr.exists():
            shutil.rmtree(self.data_mgr.data_dir)

    def connection_string(self, database: str) -> str:
        """
        Generate PostgreSQL connection string.

        Args:
            database: Database name

        Returns
        -------
            Connection string in format: postgresql://user@localhost:port/database
        """
        return f"postgresql://{self.user}@localhost:{self.port}/{database}"

    def is_running(self) -> bool:
        """
        Check if PostgreSQL is running.

        Returns
        -------
            True if PostgreSQL is running, False otherwise
        """
        return self.data_mgr.is_running()
