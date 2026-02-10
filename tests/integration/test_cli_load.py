"""
Integration test for pgosm-flex CLI command with table verification.

Tests the complete workflow: CLI invocation -> osm2pgsql processing -> table creation.
"""

from importlib import resources
from pathlib import Path
from typing import Literal

import psycopg
import pytest
from click.testing import CliRunner
from pgosm_flex.main import run_pgosm_flex

from .conftest import (
    LAYERSET_BASIC_TABLES,
    LAYERSET_DEFAULT_TABLES,
    LAYERSET_EVERYTHING_TABLES,
    LAYERSET_MINIMAL_TABLES,
    DBInfo,
)

#: Available layerset choices
LayerSet = Literal["default", "basic", "everything", "minimal"]

#: The PBF file we use for our tests
PBF_FILE = resources.files().joinpath("../../tests/data/district-of-columbia-2021-01-13.osm.pbf")

#: Expected tables to be created when skip-nested = True
EXPECTED_TABLES_SKIP_NESTED = {
    "default": LAYERSET_DEFAULT_TABLES,
    "basic": LAYERSET_BASIC_TABLES,
    "minimal": LAYERSET_MINIMAL_TABLES,
    "everything": LAYERSET_EVERYTHING_TABLES,
}


def get_command_args(
    layerset: LayerSet, test_database: DBInfo, skip_nested: bool = True
) -> list[str]:
    """
    Get arguments for pgosm-flex CLI command with table verification.
    """
    args = [
        "--ram",
        "8",  # TODO: we may want to adapt this to test runners
        "--input-file",
        str(PBF_FILE),
        "--layerset",
        layerset,
        "--skip-qgis-style",  # Skip QGIS style import
        "--subregion",
        "district-of-columbia",
        "--region",
        "north-america",
        "--db-name",
        test_database.test_db,
        "--db-port",
        test_database.port,
        "--db-user",
        test_database.user,
        "--db-host",
        test_database.host,
    ]

    if skip_nested:
        args.append("--skip-nested")

    return args


def id_layerset_skip_nested(val):
    layerset, skip_nested = val
    skip_str = "skip_nested" if skip_nested else "with_nested"

    return f"{layerset}-{skip_str}"


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(600)  # 10 minute timeout
@pytest.mark.parametrize(
    "layerset_skip_nested",
    (
        ("default", True),
        ("default", False),
        ("basic", True),
        ("everything", True),
        ("minimal", True),
    ),
    ids=id_layerset_skip_nested,
)
def test_cli_load_dc_data(test_database: DBInfo, layerset_skip_nested: tuple[LayerSet, bool]):
    """
    Test pgosm-flex CLI loads DC data and creates expected tables.

    This test:
    1. Uses click.testing.CliRunner to invoke the pgosm-flex CLI command
    2. Provides the DC PBF file via --input-file
    3. Verifies all expected tables are created in the osm schema
    4. Uses a real PostgreSQL database (via test_database fixture)
    """
    runner = CliRunner()
    layerset, skip_nested = layerset_skip_nested

    # Verify PBF file exists
    assert Path(str(PBF_FILE)).exists(), f"PBF file not found: {PBF_FILE}"

    args = get_command_args(layerset, test_database, skip_nested=skip_nested)
    result = runner.invoke(run_pgosm_flex, args)

    # Check CLI execution succeeded
    assert result.exit_code == 0, (
        f"CLI command failed with exit code {result.exit_code}:\n{result.output}"
    )

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

            expected_tables = set(EXPECTED_TABLES_SKIP_NESTED.get(layerset, []))

            # Verify all expected tables exist
            missing_tables = expected_tables - actual_tables
            assert not missing_tables, f"Missing tables: {sorted(missing_tables)}"

            # Verify we have at least the expected count
            assert len(actual_tables) >= len(expected_tables), (
                f"Expected at least {len(expected_tables)} tables, found {len(actual_tables)}"
            )

    finally:
        conn.close()
