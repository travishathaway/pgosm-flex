"""
Integration test for pgosm-flex CLI command with table verification.

Tests the complete workflow: CLI invocation -> osm2pgsql processing -> table creation.
"""

import pytest
import psycopg
from click.testing import CliRunner
from importlib import resources
from pathlib import Path

from pgosm_flex.main import run_pgosm_flex


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
    """

    runner = CliRunner()
    pbf_file = resources.files().joinpath("../../tests/data/district-of-columbia-2021-01-13.osm.pbf")

    # Verify PBF file exists
    assert Path(pbf_file).exists(), f"PBF file not found: {pbf_file}"

    result = runner.invoke(run_pgosm_flex, [
        "--ram", "8",
        "--input-file", pbf_file,
        "--layerset", "default",
        "--skip-nested",  # Skip nested polygon calculation for speed
        "--skip-qgis-style",  # Skip QGIS style import
        "--subregion", "district-of-columbia",
        "--region", "north-america",
        "--db-name", test_database.test_db,
        "--db-port", test_database.port,
        "--db-user", test_database.user,
        "--db-host", test_database.host
    ])

    # Check CLI execution succeeded
    assert result.exit_code == 0, f"CLI command failed with exit code {result.exit_code}:\n{result.output}"

    # Step 3: Verify Tables Created
    # Connect to test database
    conn = psycopg.connect(
        f"dbname={test_database.test_db} user={test_database.user} "
        f"port={test_database.port} host={test_database.host}"
    )

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
