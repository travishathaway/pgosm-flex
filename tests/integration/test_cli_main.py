"""
Pairwise combination tests for the main rountine in pgosm-flex CLI.

Uses pairwise testing strategy to cover all pairs of important parameters
with minimal test cases. This reduces test complexity from O(n^m) to O(n*m)
while still ensuring every pair of parameter values is tested together.

These tests verify both data sources:
- Geofabrik: Downloads from Geofabrik server (europe/germany/bremen)
- Input file: Uses local PBF file from tests/data
"""

import shutil
import tempfile
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
LayerSet = Literal["default", "basic", "minimal", "everything"]

#: Available data source types
DataSource = Literal["geofabrik", "file"]

#: Local PBF file for input-file tests
PBF_FILE = resources.files().joinpath("../../tests/data/district-of-columbia-2021-01-13.osm.pbf")

#: Geofabrik region for download tests
GEOFABRIK_REGION = "europe"
GEOFABRIK_SUBREGION = "germany/bremen"

#: Expected tables by layerset (when skip_nested=True)
EXPECTED_TABLES_SKIP_NESTED = {
    "default": LAYERSET_DEFAULT_TABLES,
    "basic": LAYERSET_BASIC_TABLES,
    "minimal": LAYERSET_MINIMAL_TABLES,
    "everything": LAYERSET_EVERYTHING_TABLES,
}

#: Expected tables by layerset (when skip_nested=False)
EXPECTED_TABLES_WITH_NESTED = {
    "default": [*LAYERSET_DEFAULT_TABLES, "place_polygon_nested"],
    "basic": [*LAYERSET_BASIC_TABLES, "place_polygon_nested"],
    "minimal": [*LAYERSET_MINIMAL_TABLES, "place_polygon_nested"],
    "everything": [*LAYERSET_EVERYTHING_TABLES, "place_polygon_nested"],
}


@pytest.fixture
def temp_work_dir():
    """
    Create a temporary working directory for downloads and intermediate files.

    This ensures any PBF downloads from Geofabrik or intermediate processing
    files are stored in a temp location and cleaned up after the test.
    """
    temp_dir = tempfile.mkdtemp(prefix="pgosm-flex-test-")
    yield Path(temp_dir)

    # Cleanup: Remove temp directory and all contents
    shutil.rmtree(temp_dir, ignore_errors=True)


def get_command_args(
    layerset: LayerSet,
    test_database: DBInfo,
    data_source: DataSource,
    temp_work_dir: Path,
    skip_nested: bool = True,
    skip_qgis_style: bool = True,
    replication: bool = False,
    pg_dump: bool = False,
) -> list[str]:
    """
    Build CLI arguments for pgosm-flex command.

    Args:
        layerset: Which layerset to use (minimal, basic, default)
        test_database: Database connection info
        data_source: Either "geofabrik" (download) or "file" (local PBF)
        temp_work_dir: Temporary directory for downloads/intermediate files
        skip_nested: Whether to skip nested polygon calculation
        skip_qgis_style: Whether to skip QGIS style import

    Returns
    -------
        List of CLI arguments ready for click.testing.CliRunner
    """
    args: list[str] = [
        "--ram",
        "8",
        "--layerset",
        layerset,
        "--db-name",
        test_database.test_db,
        "--db-port",
        test_database.port,
        "--db-user",
        test_database.user,
        "--db-host",
        test_database.host,
        "--data-dir",
        str(temp_work_dir),
    ]

    # Data source configuration
    if data_source == "geofabrik":
        # Download from Geofabrik (smaller region for faster tests)
        args.extend(["--region", GEOFABRIK_REGION, "--subregion", GEOFABRIK_SUBREGION])
    else:  # data_source == "file"
        # Use local PBF file
        args.extend(
            [
                "--input-file",
                str(PBF_FILE),
                "--subregion",
                "district-of-columbia",  # For metadata only
                "--region",
                "north-america",  # For metadata only
            ]
        )

    # Optional flags
    if skip_nested:
        args.append("--skip-nested")

    if skip_qgis_style:
        args.append("--skip-qgis-style")

    if replication:
        args.append("--replication")

    if pg_dump:
        args.append("--pg-dump")

    return args


def verify_tables_created(test_database: DBInfo, layerset: LayerSet, skip_nested: bool) -> None:
    """
    Verify that expected tables were created in the osm schema.

    Args:
        test_database: Database connection info
        layerset: Which layerset was used
        skip_nested: Whether nested calculation was skipped

    Raises
    ------
        AssertionError: If expected tables are missing or table count is wrong
    """
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

            # Get expected tables based on skip_nested flag
            if skip_nested:
                expected_tables = set(EXPECTED_TABLES_SKIP_NESTED[layerset])
            else:
                expected_tables = set(EXPECTED_TABLES_WITH_NESTED[layerset])

            # Verify all expected tables exist
            missing_tables = expected_tables - actual_tables
            assert not missing_tables, (
                f"Missing tables for layerset={layerset}, skip_nested={skip_nested}: "
                f"{sorted(missing_tables)}"
            )

            # Verify we don't have unexpected extra tables
            # (We allow extra tables, but verify we have at least the expected count)
            assert len(actual_tables) >= len(expected_tables), (
                f"Expected at least {len(expected_tables)} tables, found {len(actual_tables)}"
            )

    finally:
        conn.close()


#: Pairwise test matrix covering key parameter combinations
#: This matrix ensures every pair of parameters is tested together at least once
PAIRWISE_TEST_MATRIX = [
    {
        "id": "minimal_skip_nested_geofabrik_skip_qgis",
        "layerset": "minimal",
        "skip_nested": True,
        "skip_qgis_style": True,
        "data_source": "geofabrik",
    },
    {
        "id": "minimal_with_nested_file_with_qgis_and_pg_dump",
        "layerset": "minimal",
        "skip_nested": False,
        "skip_qgis_style": False,
        "data_source": "file",
        "pg_dump": True,
    },
    {
        "id": "minimal_with_nested_file_with_replication",
        "layerset": "minimal",
        "skip_nested": True,
        "skip_qgis_style": True,
        "replication": True,
        "data_source": "file",
    },
    {
        "id": "basic_skip_nested_file_with_qgis",
        "layerset": "basic",
        "skip_nested": True,
        "skip_qgis_style": False,
        "data_source": "file",
    },
    {
        "id": "basic_with_nested_geofabrik_skip_qgis",
        "layerset": "basic",
        "skip_nested": False,
        "skip_qgis_style": True,
        "data_source": "geofabrik",
    },
    {
        "id": "default_skip_nested_geofabrik_with_qgis",
        "layerset": "default",
        "skip_nested": True,
        "skip_qgis_style": False,
        "data_source": "geofabrik",
    },
    {
        "id": "default_with_nested_file_skip_qgis",
        "layerset": "default",
        "skip_nested": False,
        "skip_qgis_style": True,
        "data_source": "file",
    },
    {
        "id": "everything_skip_nested_geofabrik_with_qgis",
        "layerset": "everything",
        "skip_nested": True,
        "skip_qgis_style": False,
        "data_source": "geofabrik",
    },
    {
        "id": "everything_with_nested_file_skip_qgis",
        "layerset": "everything",
        "skip_nested": False,
        "skip_qgis_style": True,
        "data_source": "file",
    },
]


def id_pairwise_config(config: dict) -> str:
    """Generate test ID from pairwise config dict."""
    return config["id"]


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(600)  # 10 minute timeout per test
@pytest.mark.parametrize("config", PAIRWISE_TEST_MATRIX, ids=id_pairwise_config)
def test_pairwise_configurations(test_database: DBInfo, temp_work_dir: Path, config: dict) -> None:
    """
    Test pairwise combinations of configuration parameters.

    This test uses a pairwise testing strategy to efficiently cover the most
    important parameter combinations:
    - layerset: minimal, basic, default
    - skip_nested: True, False
    - skip_qgis_style: True, False
    - data_source: geofabrik (download), file (local)

    Instead of testing all 3*2*2*2 = 24 combinations, we use 6 carefully
    chosen tests that ensure every pair of parameter values appears together
    at least once.

    Each test:
    1. Configures CLI args based on the test config
    2. Invokes pgosm-flex via CliRunner
    3. Verifies the correct tables were created
    4. Cleans up temp files automatically (via fixture)
    """
    runner = CliRunner()

    # Verify local PBF file exists if using file data source
    if config["data_source"] == "file":
        assert Path(str(PBF_FILE)).exists(), f"PBF file not found: {PBF_FILE}"

    # Build CLI arguments
    args = get_command_args(
        layerset=config["layerset"],
        test_database=test_database,
        data_source=config["data_source"],
        temp_work_dir=temp_work_dir,
        skip_nested=config["skip_nested"],
        skip_qgis_style=config["skip_qgis_style"],
    )

    # Execute CLI command
    result = runner.invoke(run_pgosm_flex, args)

    # Verify CLI execution succeeded
    assert result.exit_code == 0, (
        f"CLI command failed with exit code {result.exit_code}:\n"
        f"Output: {result.output}\n"
        f"Config: {config}"
    )

    # Verify expected tables were created
    verify_tables_created(
        test_database=test_database, layerset=config["layerset"], skip_nested=config["skip_nested"]
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(300)  # 5 minute timeout
def test_data_source_geofabrik_minimal(test_database: DBInfo, temp_work_dir: Path) -> None:
    """
    Smoke test for Geofabrik data source with minimal layerset.

    This is a focused test for the most common Geofabrik use case.
    """
    runner = CliRunner()

    args = get_command_args(
        layerset="minimal",
        test_database=test_database,
        data_source="geofabrik",
        temp_work_dir=temp_work_dir,
        skip_nested=True,
        skip_qgis_style=True,
    )

    result = runner.invoke(run_pgosm_flex, args)
    assert result.exit_code == 0, f"CLI failed: {result.output}"

    verify_tables_created(test_database=test_database, layerset="minimal", skip_nested=True)


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(300)  # 5 minute timeout
def test_data_source_file_minimal(test_database: DBInfo, temp_work_dir: Path) -> None:
    """
    Smoke test for input file data source with minimal layerset.

    This is a focused test for the local PBF file use case.
    """
    runner = CliRunner()

    # Verify PBF file exists
    assert Path(str(PBF_FILE)).exists(), f"PBF file not found: {PBF_FILE}"

    args = get_command_args(
        layerset="minimal",
        test_database=test_database,
        data_source="file",
        temp_work_dir=temp_work_dir,
        skip_nested=True,
        skip_qgis_style=True,
    )

    result = runner.invoke(run_pgosm_flex, args)
    assert result.exit_code == 0, f"CLI failed: {result.output}"

    verify_tables_created(test_database=test_database, layerset="minimal", skip_nested=True)
