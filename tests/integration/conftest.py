"""Shared fixtures for integration tests."""

from pathlib import Path
from typing import NamedTuple

import psycopg
import pytest
from pgosm_flex.postgres import PostgresCluster

# Test PostgreSQL configuration
TEST_PG_PORT = 65431  # Separate from dev server (65432)
TEST_PG_USER = "postgres"
TEST_DB_MAIN = "pgosm"
TEST_DB_TESTS = "pgosm_tests"

#: Tables expected to be created with layerset = "default"
LAYERSET_DEFAULT_TABLES = [
    "amenity_line",
    "amenity_point",
    "amenity_polygon",
    "building_point",
    "building_polygon",
    "indoor_line",
    "indoor_point",
    "indoor_polygon",
    "infrastructure_line",
    "infrastructure_point",
    "infrastructure_polygon",
    "landuse_point",
    "landuse_polygon",
    "leisure_point",
    "leisure_polygon",
    "natural_line",
    "natural_point",
    "natural_polygon",
    "pgosm_flex",
    "place_line",
    "place_point",
    "place_polygon",
    # "place_polygon_nested",  # Only created when --skip-nested is False
    "poi_line",
    "poi_point",
    "poi_polygon",
    "public_transport_line",
    "public_transport_point",
    "public_transport_polygon",
    "road_line",
    "road_point",
    "road_polygon",
    "shop_point",
    "shop_polygon",
    "tags",
    "traffic_line",
    "traffic_point",
    "traffic_polygon",
    "water_line",
    "water_point",
    "water_polygon",
]

#: Tables expected to be created with layerset = "basic"
LAYERSET_BASIC_TABLES = [
    "building_combined_point",
    "landuse_point",
    "landuse_polygon",
    "pgosm_flex",
    "place_line",
    "place_point",
    "place_polygon",
    "poi_combined_point",
    "road_major",
    "unitable",
]

#: Tables expected to be created with layerset = "minimal"
LAYERSET_MINIMAL_TABLES = [
    "pgosm_flex",
    "place_line",
    "place_point",
    "place_polygon",
    "poi_combined_point",
    "road_major",
]

LAYERSET_EVERYTHING_TABLES = LAYERSET_DEFAULT_TABLES + [
    "building_combined_point",
    "poi_combined_point",
    "shop_combined_point",
    "unitable",
]


class DBInfo(NamedTuple):
    port: str
    user: str
    host: str
    main_db: str
    test_db: str


@pytest.fixture(scope="session")
def postgres_server(tmp_path_factory):
    """Start PostgreSQL server for integration tests.

    Creates a temporary PostgreSQL instance on port 65431 (separate from dev server).
    Initializes the cluster, starts the server, creates the pgosm database with PostGIS.

    Yields
    ------
        PostgresCluster: Cluster object for use by other fixtures

    Cleanup:
        Stops PostgreSQL and removes temporary data directory
    """
    # Create temporary data directory
    data_dir = tmp_path_factory.mktemp("pgdata") / "data"

    # Initialize PostgreSQL cluster
    cluster = PostgresCluster(data_dir, TEST_PG_PORT, TEST_PG_USER)

    # Setup cluster (initialize, start, create databases)
    try:
        cluster.setup(databases=[TEST_DB_MAIN], enable_postgis=True)
    except RuntimeError as e:
        raise RuntimeError(f"Failed to setup PostgreSQL cluster: {e}")

    yield cluster

    # Teardown: stop PostgreSQL and remove data directory
    cluster.teardown(remove_data=True)


@pytest.fixture(scope="session")
def db_connection_string(postgres_server):
    """Build database connection string for pgosm database.

    Returns connection string for the test PostgreSQL instance.
    """
    conn_str = postgres_server.connection_string(TEST_DB_MAIN)
    app_str = "?application_name=pgosm-flex-tests"
    return f"{conn_str}{app_str}"


@pytest.fixture(scope="session")
def db_connection(db_connection_string):
    """Create database connection for tests.

    Scope is session to reuse connection across all tests.
    Connection is automatically closed at end of session.
    """
    conn = psycopg.connect(db_connection_string)
    yield conn
    conn.close()


@pytest.fixture(scope="function")
def test_database(postgres_server):
    """Create and tear down test database for each test.

    Drops and recreates the pgosm_tests database before each test to ensure
    a clean state. Enables PostGIS extension and creates osm schema.

    Yields
    ------
        str: Connection string for test database

    Cleanup:
        Drops the test database after test completes
    """
    # Drop and recreate test database
    postgres_server.pg_mgr.drop_database(TEST_DB_TESTS)
    postgres_server.pg_mgr.create_database(TEST_DB_TESTS)
    postgres_server.pg_mgr.enable_postgis(TEST_DB_TESTS)

    # Create osm schema that tests expect
    test_conn_str = postgres_server.connection_string(TEST_DB_TESTS)
    conn = psycopg.connect(test_conn_str)
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS osm;")
        conn.commit()
    finally:
        conn.close()

    yield DBInfo(
        user=TEST_PG_USER,
        host="localhost",
        port=TEST_PG_PORT,
        main_db=TEST_DB_MAIN,
        test_db=TEST_DB_TESTS,
    )

    # Cleanup: drop test database
    postgres_server.pg_mgr.drop_database(TEST_DB_TESTS)


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
    with open(sql_file_path) as f:
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

    with open(expected_file_path) as f:
        content = f.read()

    # Strip trailing whitespace and newline to match actual output
    return content.rstrip()
