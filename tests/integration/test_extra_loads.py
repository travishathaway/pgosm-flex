"""
Integration tests for loading extra region OSM data.

Converted from tests/run-extra-loads.sh

These tests load various PBF files from extra-regions directory
into a test database and verify the data loads successfully.

WARNING: These tests are destructive - they drop and recreate the
pgosm_tests database.

Run with: pytest -m integration tests/integration/test_extra_loads.py
"""
import os
import pytest
import psycopg
import subprocess
from pathlib import Path


def get_extra_region_files(test_data_dir):
    """Get all PBF files from extra-regions directory."""
    extra_dir = test_data_dir / 'extra-regions'
    if not extra_dir.exists():
        return []
    return sorted(extra_dir.glob('*.osm.pbf'))


@pytest.fixture(scope="function")
def test_database():
    """Create and manage pgosm_tests database for testing.

    This fixture drops and recreates the database for each test.
    """
    # Connection parameters
    user = os.environ.get('POSTGRES_USER', 'postgres')
    password = os.environ.get('POSTGRES_PASSWORD')
    host = os.environ.get('POSTGRES_HOST', 'localhost')

    # Admin connection (to postgres database)
    if password:
        admin_conn_str = f'postgresql://{user}:{password}@{host}/postgres'
    else:
        admin_conn_str = f'postgresql://{user}@{host}/postgres'

    # Drop test database if exists
    admin_conn = psycopg.connect(admin_conn_str, autocommit=True)
    try:
        with admin_conn.cursor() as cur:
            cur.execute("DROP DATABASE IF EXISTS pgosm_tests;")
            cur.execute("CREATE DATABASE pgosm_tests;")
    finally:
        admin_conn.close()

    # Connect to test database and create schema
    if password:
        test_conn_str = f'postgresql://{user}:{password}@{host}/pgosm_tests'
    else:
        test_conn_str = f'postgresql://{user}@{host}/pgosm_tests'

    test_conn = psycopg.connect(test_conn_str)
    try:
        with test_conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
            cur.execute("CREATE SCHEMA IF NOT EXISTS osm;")
        test_conn.commit()

        yield test_conn_str

    finally:
        test_conn.close()


@pytest.mark.integration
@pytest.mark.slow
class TestExtraRegionLoads:
    """Test loading extra region PBF files."""

    @pytest.mark.parametrize("pbf_file",
                             get_extra_region_files(Path(__file__).parent.parent / 'data'),
                             ids=lambda x: x.name)
    @pytest.mark.timeout(300)  # 5 minute timeout per load
    def test_load_extra_region(self, test_database, pbf_file, test_data_dir):
        """Test loading an extra region PBF file.

        Parameters
        ----------
        test_database : str
            Database connection string for pgosm_tests
        pbf_file : Path
            Path to PBF file to load
        test_data_dir : Path
            Path to test data directory
        """
        # Path to flex-config directory (two levels up from tests/integration)
        flex_config_dir = test_data_dir.parent.parent / 'flex-config'

        assert flex_config_dir.exists(), f"flex-config directory not found: {flex_config_dir}"

        # Build osm2pgsql command
        # Extract database name from connection string
        db_name = 'pgosm_tests'

        cmd = [
            'osm2pgsql',
            '--slim',
            '--drop',
            '-d', db_name,
            '--output=flex',
            '--style=run-all.lua',
            str(pbf_file.absolute())
        ]

        # Run osm2pgsql
        result = subprocess.run(
            cmd,
            cwd=str(flex_config_dir),
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        # Check if successful
        assert result.returncode == 0, (
            f"osm2pgsql failed for {pbf_file.name}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

        # Verify data was loaded by checking at least one table exists
        conn = psycopg.connect(test_database)
        try:
            with conn.cursor() as cur:
                # Check if osm schema has tables
                cur.execute("""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'osm'
                    AND table_type = 'BASE TABLE'
                """)
                table_count = cur.fetchone()[0]

                assert table_count > 0, (
                    f"No tables found in osm schema after loading {pbf_file.name}"
                )
        finally:
            conn.close()


@pytest.mark.integration
@pytest.mark.slow
def test_all_extra_regions_load(test_database, test_data_dir):
    """Integration test: Load all extra regions sequentially.

    This test is separate from the parametrized test above and loads
    all regions in one go to verify they can all be processed.
    """
    extra_dir = test_data_dir / 'extra-regions'
    if not extra_dir.exists():
        pytest.skip("extra-regions directory not found")

    pbf_files = list(extra_dir.glob('*.osm.pbf'))

    if not pbf_files:
        pytest.skip("No PBF files found in extra-regions")

    loaded_count = 0
    flex_config_dir = test_data_dir.parent.parent / 'flex-config'

    for pbf_file in pbf_files:
        cmd = [
            'osm2pgsql',
            '--slim',
            '--drop',
            '-d', 'pgosm_tests',
            '--output=flex',
            '--style=run-all.lua',
            str(pbf_file.absolute())
        ]

        result = subprocess.run(
            cmd,
            cwd=str(flex_config_dir),
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            loaded_count += 1

    # All files should load successfully
    assert loaded_count == len(pbf_files), (
        f"Only {loaded_count}/{len(pbf_files)} regions loaded successfully"
    )
