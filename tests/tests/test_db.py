"""Unit tests to cover the DB module."""

import os
from urllib import parse
from unittest import mock

import pytest
from pydantic.types import SecretStr

from pgosm_flex import db, config

POSTGRES_USER = "my_pg_user"
POSTGRES_PASSWORD = "here_for_fun!@#$%^&*()"
POSTGRES_HOST_EXTERNAL = "not-intented-to-be-real"

BASE_CONFIG = {
    "region": "europe",
    "subregion": "germany/bremen",
    "ram": 8
}

PG_USER_ONLY = {
    "pg_user": POSTGRES_USER,
    "pg_password": "",
    **BASE_CONFIG
}
PG_USER_AND_PW = {
    "pg_user": POSTGRES_USER,
    "pg_password": POSTGRES_PASSWORD,
    **BASE_CONFIG
}
POSTGRES_HOST_NON_LOCAL = {
    "pg_host": POSTGRES_HOST_EXTERNAL,
    "pg_user": POSTGRES_USER,
    "pg_password": POSTGRES_PASSWORD,
    **BASE_CONFIG
}


@pytest.fixture
def db_fetchone(mocker):
    """Factory fixture that mocks database connection and returns configurable fetchone result.

    Returns a function that accepts a return_value parameter for fetchone().
    """
    def _mock_db_fetchone(return_value):
        mock_config = mocker.Mock()
        mock_config.database.connection_string.return_value = "postgresql://test@localhost/pgosm"
        mocker.patch('pgosm_flex.db.get_config', return_value=mock_config)

        # Mock the database connection and cursor
        mock_cursor = mocker.Mock()
        mock_cursor.fetchone.return_value = return_value

        mock_conn = mocker.Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = mocker.Mock(return_value=mock_conn)
        mock_conn.__exit__ = mocker.Mock(return_value=None)

        mocker.patch('pgosm_flex.db.get_db_conn', return_value=mock_conn)

        return mock_cursor

    return _mock_db_fetchone


def test_pg_conn_parts_user_only_returns_expected_values():
    with config.config_context(config.init_config(PG_USER_ONLY)) as conf:
        expected_user = POSTGRES_USER
        expected_pw = SecretStr("")

        assert expected_user == conf.database.user
        assert expected_pw == conf.database.password


def test_pg_conn_parts_user_w_pw_returns_expected_values():
    with config.config_context(config.init_config(PG_USER_AND_PW)) as conf:
        expected_user = POSTGRES_USER
        expected_pw = SecretStr(POSTGRES_PASSWORD)

        assert expected_user == conf.database.user
        assert expected_pw == conf.database.password


def test_connection_string_user_only_returns_expected_string():
    with config.config_context(config.init_config(PG_USER_ONLY)) as conf:
        expected = f"postgresql://{POSTGRES_USER}:@localhost:5432/pgosm?application_name=pgosm-flex"
        assert expected == conf.database.connection_string()


def test_connection_string_user_w_pw_returns_expected_string():
    with config.config_context(config.init_config(PG_USER_AND_PW)) as conf:
        password_safe = parse.quote(POSTGRES_PASSWORD)
        expected = f"postgresql://{POSTGRES_USER}:{password_safe}@localhost:5432/pgosm?application_name=pgosm-flex"

        result = conf.database.connection_string()

        assert expected == result


def test_admin_connection_string_external_returns_expected_string():
    """
    Non-Docker Postgres connection uses the same connection string for
    standard & admin connections. Only use of admin connection w/ external
    Postgres is version check.
    """
    with config.config_context(config.init_config(POSTGRES_HOST_NON_LOCAL)) as conf:
        password_safe = parse.quote(POSTGRES_PASSWORD)
        expected = f"postgresql://{POSTGRES_USER}:{password_safe}@{POSTGRES_HOST_EXTERNAL}:5432/pgosm?application_name=pgosm-flex"
        result_standard = conf.database.connection_string()
        result_admin = conf.database.connection_string(admin=True)

        assert expected == result_standard
        assert expected == result_admin


def test_pg_version_check_returns_int(db_fetchone):
    """Test that pg_version_check returns an integer without connecting to a real database."""
    # Use the fixture factory to mock the database with a specific return value
    db_fetchone((140000,))  # PostgreSQL 14 version

    # Call the function
    result = db.pg_version_check()

    # Verify it returns an int and has the expected value
    assert isinstance(result, int)
    assert result == 140000


def test_get_prior_import_returns_expected_type(mocker):
    """Test that get_prior_import returns a dict."""
    # Mock the config
    mock_config = mocker.Mock()
    mock_config.database.connection_string.return_value = "postgresql://test@localhost/pgosm"
    mocker.patch('pgosm_flex.db.get_config', return_value=mock_config)

    # Mock the database connection and cursor
    # The cursor.execute() returns self, and .fetchone() returns None
    mock_cursor = mocker.Mock()
    mock_cursor.execute.return_value = mock_cursor  # execute returns self for chaining
    mock_cursor.fetchone.return_value = None  # No prior import

    mock_conn = mocker.Mock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__ = mocker.Mock(return_value=mock_conn)
    mock_conn.__exit__ = mocker.Mock(return_value=None)

    mocker.patch('pgosm_flex.db.get_db_conn', return_value=mock_conn)

    # Call the function
    result = db.get_prior_import(schema_name="osm")

    # Verify it returns an empty dict when no prior import exists
    assert isinstance(result, dict)
    assert result == {}


def test_fix_pg_dump_create_public_replaces_create_schema(tmp_path):
    """Test that fix_pg_dump_create_public replaces CREATE SCHEMA public correctly."""
    # Create a temporary SQL file with the problematic CREATE SCHEMA statement
    sql_file = tmp_path / "test_dump.sql"
    sql_file.write_text("""-- PostgreSQL database dump
        --

        CREATE SCHEMA public;

        CREATE EXTENSION IF NOT EXISTS postgis;

        -- More SQL content here
        CREATE TABLE public.test (id INTEGER);
    """)

    # Run the function
    db.fix_pg_dump_create_public(str(sql_file))

    # Read the modified content
    content = sql_file.read_text()

    # Verify the replacement was made
    assert 'CREATE SCHEMA IF NOT EXISTS public;' in content
    assert 'CREATE SCHEMA public;' not in content
    # Ensure other content is preserved
    assert 'CREATE EXTENSION IF NOT EXISTS postgis;' in content
    assert 'CREATE TABLE public.test (id INTEGER);' in content


def test_fix_pg_dump_create_public_handles_multiple_occurrences(tmp_path):
    """Test that fix_pg_dump_create_public replaces all occurrences."""
    # Create a temporary file with multiple CREATE SCHEMA public statements
    sql_file = tmp_path / "test_dump_multiple.sql"
    sql_file.write_text("""CREATE SCHEMA public;
        CREATE SCHEMA other;
        CREATE SCHEMA public;
    """)

    # Run the function
    db.fix_pg_dump_create_public(str(sql_file))

    # Read the modified content
    content = sql_file.read_text()

    # Verify both replacements were made
    assert content.count('CREATE SCHEMA IF NOT EXISTS public;') == 2
    assert 'CREATE SCHEMA public;' not in content
    # Ensure other schema statements are not affected
    assert 'CREATE SCHEMA other;' in content


def test_fix_pg_dump_create_public_handles_empty_file(tmp_path):
    """Test that fix_pg_dump_create_public handles empty files gracefully."""
    sql_file = tmp_path / "empty.sql"
    sql_file.write_text("")

    # Should not raise an error
    db.fix_pg_dump_create_public(str(sql_file))

    # File should remain empty
    assert sql_file.read_text() == ""


def test_fix_pg_dump_create_public_preserves_content_without_target_string(tmp_path):
    """Test that files without CREATE SCHEMA public; are left unchanged."""
    original_content = """-- PostgreSQL database dump
        CREATE SCHEMA other;
        CREATE TABLE test (id INTEGER);
    """
    sql_file = tmp_path / "no_match.sql"
    sql_file.write_text(original_content)

    # Run the function
    db.fix_pg_dump_create_public(str(sql_file))

    # Content should be identical
    assert sql_file.read_text() == original_content
