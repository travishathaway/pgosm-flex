"""
Integration test for pgosm-flex CLI command with table verification.

Tests the complete workflow: CLI invocation -> osm2pgsql processing -> table creation.
"""

import re
import pytest
import psycopg
from click.testing import CliRunner
from pathlib import Path

from pgosm_flex.main import run_pgosm_flex


def parse_connection_string(conn_str: str) -> dict:
    """
    Parse PostgreSQL connection string into components.

    Parameters
    ----------
    conn_str : str
        Connection string like "postgresql://user@localhost:5432/dbname?params"

    Returns
    -------
    dict
        Dictionary with keys: user, host, port, dbname
    """
    # Format: postgresql://user@host:port/dbname?application_name=...
    pattern = r"postgresql://([^@]+)@([^:]+):(\d+)/([^?]+)"
    match = re.match(pattern, conn_str)
    if not match:
        raise ValueError(f"Cannot parse connection string: {conn_str}")

    return {
        "user": match.group(1),
        "host": match.group(2),
        "port": match.group(3),
        "dbname": match.group(4),
    }


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(600)  # 10 minute timeout
def test_cli_load_dc_data(test_database, monkeypatch):
    """
    Test pgosm-flex CLI loads DC data and creates expected tables.

    This test:
    1. Uses click.testing.CliRunner to invoke the pgosm-flex CLI command
    2. Provides the DC PBF file via --input-file
    3. Verifies all expected tables are created in the osm schema
    4. Uses a real PostgreSQL database (via test_database fixture)

    Parameters
    ----------
    test_database : str
        Database connection string from conftest.py fixture
    monkeypatch : pytest.MonkeyPatch
        Pytest fixture for patching environment variables
    """
    # Step 1: Setup Environment Variables
    # Parse connection string: postgresql://user@host:port/dbname?params
    conn_parts = parse_connection_string(test_database)
    monkeypatch.setenv("POSTGRES_HOST", conn_parts["host"])
    monkeypatch.setenv("POSTGRES_PORT", conn_parts["port"])
    monkeypatch.setenv("POSTGRES_DB", conn_parts["dbname"])
    monkeypatch.setenv("POSTGRES_USER", conn_parts["user"])

    # Step 2: Invoke CLI Command
    runner = CliRunner()
    pbf_file = "/Users/travishathaway/dev/pgosm-flex/tests/data/district-of-columbia-2021-01-13.osm.pbf"

    # Verify PBF file exists
    assert Path(pbf_file).exists(), f"PBF file not found: {pbf_file}"

    result = runner.invoke(run_pgosm_flex, [
        "--ram", "8",
        "--input-file", pbf_file,
        "--layerset", "default",
        "--skip-nested",  # Skip nested polygon calculation for speed
        "--skip-qgis-style",  # Skip QGIS style import
    ])

    # Check CLI execution succeeded
    assert result.exit_code == 0, f"CLI command failed with exit code {result.exit_code}:\n{result.output}"

    # Step 3: Verify Tables Created
    # Connect to test database
    conn = psycopg.connect(test_database)
    try:
        with conn.cursor() as cursor:
            # Query for all tables in osm schema
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'osm'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)

            actual_tables = {row[0] for row in cursor.fetchall()}

            # Expected tables from default layerset (46 tables)
            expected_tables = {
                # amenity (3)
                "amenity_point", "amenity_line", "amenity_polygon",
                # building (2)
                "building_point", "building_polygon",
                # indoor (3)
                "indoor_point", "indoor_line", "indoor_polygon",
                # infrastructure (3)
                "infrastructure_point", "infrastructure_line", "infrastructure_polygon",
                # landuse (2)
                "landuse_point", "landuse_polygon",
                # leisure (2)
                "leisure_point", "leisure_polygon",
                # natural (3)
                "natural_point", "natural_line", "natural_polygon",
                # place (3)
                "place_point", "place_line", "place_polygon",
                # poi (3)
                "poi_point", "poi_line", "poi_polygon",
                # public_transport (3)
                "public_transport_point", "public_transport_line", "public_transport_polygon",
                # road (3)
                "road_point", "road_line", "road_polygon",
                # shop (2)
                "shop_point", "shop_polygon",
                # tags (1)
                "tags",
                # traffic (3)
                "traffic_point", "traffic_line", "traffic_polygon",
                # water (3)
                "water_point", "water_line", "water_polygon",
            }

            # Verify all expected tables exist
            missing_tables = expected_tables - actual_tables
            assert not missing_tables, f"Missing tables: {sorted(missing_tables)}"

            # Check for extra tables (may include metadata tables like pgosm_flex)
            extra_tables = actual_tables - expected_tables
            # Note: pgosm_flex creates additional metadata tables, so this is informational
            if extra_tables:
                print(f"Note: Extra tables found (may be metadata): {sorted(extra_tables)}")

            # Verify we have at least the expected count
            assert len(actual_tables) >= len(expected_tables), \
                f"Expected at least {len(expected_tables)} tables, found {len(actual_tables)}"

            print(f"✓ Successfully verified {len(expected_tables)} expected tables in osm schema")

    finally:
        conn.close()
