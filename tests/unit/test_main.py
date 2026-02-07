"""Unit tests to cover the DB module."""

import io
import os
import subprocess
import pytest
from pathlib import Path

from pgosm_flex import main as pgosm_flex, config


REGION_US = "north-america/us"
SUBREGION_DC = "district-of-columbia"
LAYERSET = "default"
PGOSM_DATE = "2021-12-02"


@pytest.fixture
def default_config():
    """Default configuration for tests."""
    yield config.config_context(
        config.init_config(
            {
                "region": REGION_US,
                "subregion": SUBREGION_DC,
                "srid": "3857",
                "language": None,
                "pgosm_date": PGOSM_DATE,
                "layerset": LAYERSET,
                "layerset_path": None,
                "schema_name": "osm",
                "skip_nested": True,
                "ram": 8,
            }
        )
    )


@pytest.fixture
def config_region_only():
    """Configuration with region only (no subregion)."""
    yield config.config_context(
        config.init_config(
            {
                "region": "north-america",
                "subregion": None,
                "srid": "3857",
                "language": None,
                "pgosm_date": PGOSM_DATE,
                "layerset": LAYERSET,
                "layerset_path": None,
                "schema_name": "osm",
                "skip_nested": True,
                "ram": 8,
            }
        )
    )


@pytest.fixture
def config_custom_layerset():
    """Configuration with custom layerset path."""
    # Get the absolute path to the layersets directory
    layersets_dir = Path(__file__).parent / "layersets"

    def _config(layerset_name):
        return config.config_context(
            config.init_config(
                {
                    "region": "north-america",
                    "subregion": None,
                    "srid": "3857",
                    "language": None,
                    "pgosm_date": PGOSM_DATE,
                    "layerset": layerset_name,
                    "layerset_path": layersets_dir,
                    "schema_name": "osm",
                    "skip_nested": True,
                    "ram": 8,
                }
            )
        )
    return _config


def test_get_paths_returns_dict(default_config):
    with default_config:
        expected = dict
        actual = pgosm_flex.get_paths()
        assert expected == type(actual)


def test_validate_region_inputs_raises_ValueError_no_region_or_input(default_config):
    with default_config:
        region = None
        subregion = None
        input_file = None

        with pytest.raises(ValueError):
            pgosm_flex.validate_region_inputs(region, subregion, input_file)


def test_validate_region_inputs_raises_ValueError_subregion_wout_region(default_config):
    with default_config:
        region = None
        subregion = "subregion-value"
        input_file = "some-value"

        with pytest.raises(ValueError):
            pgosm_flex.validate_region_inputs(region, subregion, input_file)


def test_validate_region_inputs_raises_ValueError_region_should_have_subregion(
    default_config,
):
    with default_config:
        region = "north-america/us"
        subregion = None
        input_file = None

        with pytest.raises(ValueError):
            pgosm_flex.validate_region_inputs(region, subregion, input_file)


def test_get_export_full_path_returns_expected_str(default_config):
    with default_config:
        export_filename = "relative-path"
        out_path = "/tmp/not/real"
        expected = f"{out_path}/{export_filename}"
        result = pgosm_flex.get_export_full_path(out_path, export_filename)
        assert expected == result


def test_get_export_filename_slash_to_dash(default_config):
    """Ensure region & subregion have slash "/" changed to dash "-"

    Also tests the filename w/ region & subregion - no need for an additional
    test covering that behavior.
    """
    with default_config:
        input_file = None
        result = pgosm_flex.get_export_filename(input_file)
        expected = "north-america-us-district-of-columbia-default-2021-12-02.sql"
        assert expected == result


def test_get_export_filename_input_file_defined_overrides_region_subregion(
    default_config,
):
    with default_config:
        input_file = "/my/inputfile.osm.pbf"
        result = pgosm_flex.get_export_filename(input_file)
        expected = "/my/inputfile-default-2021-12-02.sql"
        assert expected == result


def test_get_export_filename_region_only(config_region_only):
    """Override Subregion to None"""
    with config_region_only:
        input_file = None
        result = pgosm_flex.get_export_filename(input_file)
        expected = "north-america-default-2021-12-02.sql"
        assert expected == result


def test_layerset_include_place_returns_boolean(config_region_only):
    with config_region_only:
        paths = pgosm_flex.get_paths()
        result = pgosm_flex.layerset_include_place(flex_path=paths["flex_path"])
        expected = bool
        actual = type(result)
        assert expected == actual


def test_layerset_include_place_returns_True_with_default_layerset(config_region_only):
    with config_region_only:
        paths = pgosm_flex.get_paths()
        actual = pgosm_flex.layerset_include_place(flex_path=paths["flex_path"])
        expected = True
        assert expected == actual


def test_layerset_include_place_returns_false_when_place_false_in_ini(
    config_custom_layerset,
):
    with config_custom_layerset("place_false"):
        paths = pgosm_flex.get_paths()
        actual = pgosm_flex.layerset_include_place(flex_path=paths["flex_path"])
        expected = False
        assert expected == actual


def test_layerset_include_place_returns_false_when_place_missing_in_ini(
    config_custom_layerset,
):
    with config_custom_layerset("place_missing"):
        paths = pgosm_flex.get_paths()
        actual = pgosm_flex.layerset_include_place(flex_path=paths["flex_path"])
        expected = False
        assert expected == actual


def test_layerset_include_place_returns_true_when_place_true_in_ini(
    config_custom_layerset,
):
    with config_custom_layerset("place_true"):
        paths = pgosm_flex.get_paths()
        actual = pgosm_flex.layerset_include_place(flex_path=paths["flex_path"])
        expected = True
        assert expected == actual


# Tests for database CLI options


def test_database_cli_options_with_defaults():
    """Test that database options default correctly when not specified."""
    test_config = config.config_context(
        config.init_config(
            {
                "region": REGION_US,
                "subregion": SUBREGION_DC,
                "srid": "3857",
                "language": None,
                "pgosm_date": PGOSM_DATE,
                "layerset": LAYERSET,
                "layerset_path": None,
                "schema_name": "osm",
                "skip_nested": True,
                "ram": 8,
                # Database options not specified - should use defaults
            }
        )
    )

    with test_config:
        cfg = config.get_config()
        assert cfg.database.host == "localhost"
        assert cfg.database.port == 5432
        assert cfg.database.database == "pgosm"
        assert cfg.database.user == "postgres"
        assert cfg.database.password is None


def test_database_cli_options_with_custom_values():
    """Test that database CLI options override defaults."""
    test_config = config.config_context(
        config.init_config(
            {
                "region": REGION_US,
                "subregion": SUBREGION_DC,
                "srid": "3857",
                "language": None,
                "pgosm_date": PGOSM_DATE,
                "layerset": LAYERSET,
                "layerset_path": None,
                "schema_name": "osm",
                "skip_nested": True,
                "ram": 8,
                # Custom database options
                "pg_host": "custom-host",
                "pg_port": 5433,
                "pg_dbname": "custom_db",
                "pg_user": "custom_user",
                "pg_password": "custom_password",
            }
        )
    )

    with test_config:
        cfg = config.get_config()
        assert cfg.database.host == "custom-host"
        assert cfg.database.port == 5433
        assert cfg.database.database == "custom_db"
        assert cfg.database.user == "custom_user"
        assert cfg.database.password.get_secret_value() == "custom_password"


def test_database_connection_string_with_custom_params():
    """Test that connection string includes custom database parameters."""
    test_config = config.config_context(
        config.init_config(
            {
                "region": REGION_US,
                "subregion": SUBREGION_DC,
                "srid": "3857",
                "language": None,
                "pgosm_date": PGOSM_DATE,
                "layerset": LAYERSET,
                "layerset_path": None,
                "schema_name": "osm",
                "skip_nested": True,
                "ram": 8,
                "pg_host": "db.example.com",
                "pg_port": 5433,
                "pg_dbname": "my_osm",
                "pg_user": "osm_user",
                "pg_password": "secret123",
            }
        )
    )

    with test_config:
        cfg = config.get_config()
        conn_str = cfg.database.connection_string()

        # Check connection string contains all custom values
        assert "db.example.com" in conn_str
        assert "5433" in conn_str
        assert "my_osm" in conn_str
        assert "osm_user" in conn_str
        assert "secret123" in conn_str
        assert "application_name=pgosm-flex" in conn_str


def test_database_connection_string_without_password():
    """Test connection string format when no password is provided."""
    test_config = config.config_context(
        config.init_config(
            {
                "region": REGION_US,
                "subregion": SUBREGION_DC,
                "srid": "3857",
                "language": None,
                "pgosm_date": PGOSM_DATE,
                "layerset": LAYERSET,
                "layerset_path": None,
                "schema_name": "osm",
                "skip_nested": True,
                "ram": 8,
                "pg_host": "localhost",
                "pg_user": "testuser",
                # No password
            }
        )
    )

    with test_config:
        cfg = config.get_config()
        conn_str = cfg.database.connection_string()

        # Should not have colon after username when no password
        assert "testuser@localhost" in conn_str
        assert ":@" not in conn_str  # No password separator


# Tests for lua config generation functionality


def test_write_index_config_with_existing_file(default_config):
    """Test _write_index_config() with an existing index INI file."""
    with default_config:
        paths = pgosm_flex.get_paths()
        flex_path = paths["flex_path"]

        # Use a StringIO to capture the output
        output = io.StringIO()

        # Test with a layer that has an index file (poi)
        pgosm_flex._write_index_config(output, flex_path, "poi")

        result = output.getvalue()

        # Verify it generates a valid Lua table structure
        assert result.startswith("{")
        assert result.endswith("}")
        # Should contain at least one geometry type section
        assert "point" in result or "line" in result or "polygon" in result or "all" in result


def test_write_index_config_with_missing_file(default_config):
    """Test _write_index_config() gracefully handles missing index files."""
    with default_config:
        paths = pgosm_flex.get_paths()
        flex_path = paths["flex_path"]

        output = io.StringIO()

        # Test with a nonexistent layer
        pgosm_flex._write_index_config(output, flex_path, "nonexistent_layer")

        result = output.getvalue()

        # Should return empty table for missing file
        assert result == "{}"


def test_generate_lua_config_sets_environment_variable(default_config):
    """Test that generate_lua_config() sets the PGOSM_LUA_CONFIG environment variable."""
    with default_config:
        # Ensure env var is not set initially
        if "PGOSM_LUA_CONFIG" in os.environ:
            del os.environ["PGOSM_LUA_CONFIG"]

        with pgosm_flex.generate_lua_config():
            # Should be set within the context
            assert "PGOSM_LUA_CONFIG" in os.environ
            assert len(os.environ["PGOSM_LUA_CONFIG"]) > 0

        # Should be cleaned up after context exit
        assert "PGOSM_LUA_CONFIG" not in os.environ


def test_generate_lua_config_contains_core_values(default_config):
    """Test that generated config contains all core configuration values."""
    with default_config:
        with pgosm_flex.generate_lua_config():
            lua_config = os.environ["PGOSM_LUA_CONFIG"]

            # Check for core config values
            assert "srid = 3857" in lua_config
            assert "schema_name = 'osm'" in lua_config
            assert f"pgosm_date = '{PGOSM_DATE}'" in lua_config
            assert "pgosm_language = " in lua_config


def test_generate_lua_config_contains_layers_section(default_config):
    """Test that generated config contains the layers section."""
    with default_config:
        with pgosm_flex.generate_lua_config():
            lua_config = os.environ["PGOSM_LUA_CONFIG"]

            # Should have layers section
            assert "layers = {" in lua_config
            # Should have some layers defined
            assert "amenity = " in lua_config
            assert "building = " in lua_config
            assert "poi = " in lua_config
            # Values should be Lua booleans
            assert "true" in lua_config or "false" in lua_config


def test_generate_lua_config_contains_indexes_section(default_config):
    """Test that generated config contains the indexes section."""
    with default_config:
        with pgosm_flex.generate_lua_config():
            lua_config = os.environ["PGOSM_LUA_CONFIG"]

            # Should have indexes section
            assert "indexes = {" in lua_config


def test_generate_lua_config_returns_valid_lua(default_config):
    """Test that generated config returns a valid Lua table."""
    with default_config:
        with pgosm_flex.generate_lua_config():
            lua_config = os.environ["PGOSM_LUA_CONFIG"]

            # Should start with comment and return config
            assert lua_config.startswith("-- Auto-generated")
            assert "return config" in lua_config


def test_generate_lua_config_valid_lua_syntax(default_config):
    """Test that generated config has valid Lua syntax using luac."""
    with default_config:
        with pgosm_flex.generate_lua_config():
            lua_config = os.environ["PGOSM_LUA_CONFIG"]

            # Try to validate syntax with luac if available
            try:
                result = subprocess.run(
                    ["luac", "-p", "-"],
                    input=lua_config,
                    text=True,
                    capture_output=True,
                    timeout=5
                )
                # If luac is available, check it validates successfully
                assert result.returncode == 0, f"Lua syntax error: {result.stderr}"
            except FileNotFoundError:
                # luac not available, skip this check
                pytest.skip("luac not available for syntax validation")


def test_generate_lua_config_can_be_loaded_by_lua(default_config):
    """Test that Lua can actually load and execute the generated config."""
    with default_config:
        with pgosm_flex.generate_lua_config():
            # Create a simple Lua test script that loads the config
            test_script = '''
local config_code = os.getenv("PGOSM_LUA_CONFIG")
if not config_code then
    os.exit(1)
end

local func, err = load(config_code)
if not func then
    print("Load error: " .. err)
    os.exit(1)
end

local config = func()
if not config then
    print("Config is nil")
    os.exit(1)
end

-- Verify config has expected structure
if not config.srid then os.exit(1) end
if not config.schema_name then os.exit(1) end
if not config.layers then os.exit(1) end
if not config.indexes then os.exit(1) end

os.exit(0)
            '''

            try:
                result = subprocess.run(
                    ["lua", "-e", test_script],
                    env=os.environ.copy(),
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                assert result.returncode == 0, f"Lua execution failed: {result.stderr}"
            except FileNotFoundError:
                pytest.skip("lua interpreter not available for testing")


def test_generate_lua_config_with_custom_language(default_config):
    """Test that custom language is included in generated config."""
    # Create config with custom language
    test_config = config.config_context(
        config.init_config(
            {
                "region": REGION_US,
                "subregion": SUBREGION_DC,
                "srid": "3857",
                "language": "es",  # Spanish
                "pgosm_date": PGOSM_DATE,
                "layerset": LAYERSET,
                "layerset_path": None,
                "schema_name": "osm",
                "skip_nested": True,
                "ram": 8,
            }
        )
    )

    with test_config:
        with pgosm_flex.generate_lua_config():
            lua_config = os.environ["PGOSM_LUA_CONFIG"]
            assert "pgosm_language = 'es'" in lua_config


def test_generate_lua_config_with_custom_srid(default_config):
    """Test that custom SRID is included in generated config."""
    # Create config with custom SRID
    test_config = config.config_context(
        config.init_config(
            {
                "region": REGION_US,
                "subregion": SUBREGION_DC,
                "srid": "4326",  # WGS84
                "language": None,
                "pgosm_date": PGOSM_DATE,
                "layerset": LAYERSET,
                "layerset_path": None,
                "schema_name": "osm",
                "skip_nested": True,
                "ram": 8,
            }
        )
    )

    with test_config:
        with pgosm_flex.generate_lua_config():
            lua_config = os.environ["PGOSM_LUA_CONFIG"]
            assert "srid = 4326" in lua_config


def test_generate_lua_config_with_custom_schema(default_config):
    """Test that custom schema name is included in generated config."""
    # Create config with custom schema
    test_config = config.config_context(
        config.init_config(
            {
                "region": REGION_US,
                "subregion": SUBREGION_DC,
                "srid": "3857",
                "language": None,
                "pgosm_date": PGOSM_DATE,
                "layerset": LAYERSET,
                "layerset_path": None,
                "schema_name": "custom_schema",
                "skip_nested": True,
                "ram": 8,
            }
        )
    )

    with test_config:
        with pgosm_flex.generate_lua_config():
            lua_config = os.environ["PGOSM_LUA_CONFIG"]
            assert "schema_name = 'custom_schema'" in lua_config


def test_generate_lua_config_cleanup_on_exception(default_config):
    """Test that environment variable is cleaned up even if exception occurs."""
    with default_config:
        try:
            with pgosm_flex.generate_lua_config():
                # Verify it's set
                assert "PGOSM_LUA_CONFIG" in os.environ
                # Simulate an exception
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Should still be cleaned up after exception
        assert "PGOSM_LUA_CONFIG" not in os.environ
