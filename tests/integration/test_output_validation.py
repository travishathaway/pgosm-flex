"""
Integration tests for SQL query output validation.

Converted from tests/run-output-tests.sh

These tests run SQL queries against the pgosm database and compare
the output with expected results. Tests require a pre-loaded database
with OSM data (typically district-of-columbia test data).

Run with: pytest -m integration tests/integration/test_output_validation.py
"""

import pytest
from pathlib import Path
from .conftest import execute_sql_file, read_expected_output


def get_sql_test_files(sql_dir):
    """Get all SQL test files from sql directory.

    Returns list of (sql_file, expected_file) tuples.
    """
    sql_files = []
    for sql_file in sorted(sql_dir.glob("*.sql")):
        expected_file = sql_dir.parent / "expected" / f"{sql_file.stem}.out"
        # Only include if expected output exists
        if expected_file.exists():
            sql_files.append((sql_file, expected_file))
    return sql_files


@pytest.mark.integration
@pytest.mark.output
class TestSQLOutputValidation:
    """Test SQL queries produce expected output."""

    @pytest.mark.parametrize(
        "sql_file,expected_file",
        get_sql_test_files(Path(__file__).parent.parent / "sql"),
        ids=lambda x: x.stem if isinstance(x, Path) else str(x),
    )
    @pytest.mark.timeout(30)  # 30 second timeout per query
    def test_sql_output(self, db_connection, sql_file, expected_file):
        """Test that SQL query produces expected output.

        Parameters
        ----------
        db_connection : psycopg.Connection
            Database connection fixture
        sql_file : Path
            Path to SQL file to execute
        expected_file : Path
            Path to expected output file
        """
        # Execute SQL query
        actual_output = execute_sql_file(db_connection, sql_file)

        # Read expected output
        expected_output = read_expected_output(expected_file)

        # Compare outputs
        assert actual_output == expected_output, (
            f"\nSQL query output mismatch for {sql_file.name}\n"
            f"Expected:\n{expected_output}\n"
            f"Actual:\n{actual_output}\n"
        )


@pytest.mark.integration
@pytest.mark.output
class TestSpecificQueries:
    """Test specific SQL queries with detailed assertions."""

    def test_pgosm_road_row_count(self, db_connection, sql_dir, expected_dir):
        """Test pgosm.road table has expected row count."""
        sql_file = sql_dir / "pgosm_road_row_count.sql"
        expected_file = expected_dir / "pgosm_road_row_count.out"

        actual = execute_sql_file(db_connection, sql_file)
        expected = read_expected_output(expected_file)

        assert actual == expected
        # Also verify it's a positive integer
        assert int(actual) > 0

    def test_road_line_aggregates(self, db_connection, sql_dir, expected_dir):
        """Test road_line table aggregations."""
        sql_file = sql_dir / "road_line_aggregates.sql"
        expected_file = expected_dir / "road_line_aggregates.out"

        if not sql_file.exists():
            pytest.skip(f"SQL file not found: {sql_file}")

        actual = execute_sql_file(db_connection, sql_file)
        expected = read_expected_output(expected_file)

        assert actual == expected

        # Verify structure: should be 6 pipe-delimited integers
        parts = actual.split("|")
        assert len(parts) == 6
        # All should be positive integers
        for part in parts:
            assert int(part) > 0

    def test_amenity_point_osm_type_count(self, db_connection, sql_dir):
        """Test amenity_point osm_type counts are reasonable."""
        sql_file = sql_dir / "amenity_point_osm_type_count.sql"

        actual = execute_sql_file(db_connection, sql_file)

        # Should have multiple rows
        lines = actual.strip().split("\n")
        assert len(lines) > 0

        # Each line should be osm_type|count format
        for line in lines:
            parts = line.split("|")
            assert len(parts) == 2
            osm_type, count = parts
            assert osm_type  # Non-empty
            assert int(count) > 0  # Positive count
