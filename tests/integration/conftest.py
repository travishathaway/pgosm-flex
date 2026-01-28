"""Shared fixtures for integration tests."""

import os
import pytest
import psycopg
from pathlib import Path


@pytest.fixture(scope="session")
def db_connection_string():
    """Build database connection string from environment variables.

    Returns connection string for pgosm database.
    Falls back to defaults if environment variables not set.
    """
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    database = "pgosm"

    app_str = "?application_name=pgosm-flex-tests"

    if password:
        conn_str = f"postgresql://{user}:{password}@{host}/{database}{app_str}"
    else:
        conn_str = f"postgresql://{user}@{host}/{database}{app_str}"

    return conn_str


@pytest.fixture(scope="session")
def db_connection(db_connection_string):
    """Create database connection for tests.

    Scope is session to reuse connection across all tests.
    Connection is automatically closed at end of session.
    """
    conn = psycopg.connect(db_connection_string)
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def test_data_dir():
    """Return path to test data directory."""
    return Path(__file__).parent.parent / "data"


@pytest.fixture(scope="session")
def sql_dir():
    """Return path to SQL test files."""
    return Path(__file__).parent.parent / "sql"


@pytest.fixture(scope="session")
def expected_dir():
    """Return path to expected output files."""
    return Path(__file__).parent.parent / "expected"


def execute_sql_file(conn, sql_file_path):
    """Execute SQL file and return results in pipe-delimited format.

    Parameters
    ----------
    conn : psycopg.Connection
        Database connection
    sql_file_path : Path
        Path to SQL file

    Returns
    -------
    str
        Query results in pipe-delimited format (matching psql -tA output)
    """
    with open(sql_file_path, "r") as f:
        sql = f.read()

    with conn.cursor() as cur:
        cur.execute(sql)

        # Get results in pipe-delimited format
        rows = cur.fetchall()
        if not rows:
            return ""

        # Format as pipe-delimited (matching psql -tA output)
        lines = []
        for row in rows:
            # Convert values to strings and join with pipe
            line = "|".join(str(val) if val is not None else "" for val in row)
            lines.append(line)

        return "\n".join(lines)


def read_expected_output(expected_file_path):
    """Read expected output file.

    Parameters
    ----------
    expected_file_path : Path
        Path to expected output file

    Returns
    -------
    str
        Expected output content (stripped of trailing whitespace)
    """
    if not expected_file_path.exists():
        return ""

    with open(expected_file_path, "r") as f:
        content = f.read()

    # Strip trailing whitespace and newline to match actual output
    return content.rstrip()
