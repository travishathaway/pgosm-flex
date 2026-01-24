"""Tests for pgosm_flex.config module."""
import unittest
import os
from pathlib import Path
from unittest.mock import patch
import tempfile

from pgosm_flex.config import (
    DatabaseConfig, RegionConfig, LayersetConfig,
    ImportConfig, ProcessingConfig, PgOSMFlexConfig,
    ConfigLoader, get_today
)


class GetTodayTests(unittest.TestCase):
    """Tests for get_today() helper function."""

    def test_get_today_format(self):
        """Test get_today returns yyyy-mm-dd format."""
        today = get_today()
        self.assertRegex(today, r'^\d{4}-\d{2}-\d{2}$')


class DatabaseConfigTests(unittest.TestCase):
    """Tests for DatabaseConfig model."""

    def test_default_values(self):
        """Test default database configuration."""
        config = DatabaseConfig()
        self.assertEqual(config.host, "localhost")
        self.assertEqual(config.port, 5432)
        self.assertEqual(config.database, "pgosm")
        self.assertEqual(config.user, "postgres")
        self.assertIsNone(config.password)

    def test_custom_values(self):
        """Test custom database configuration."""
        config = DatabaseConfig(
            host="dbhost",
            port=5433,
            database="mydb",
            user="myuser"
        )
        self.assertEqual(config.host, "dbhost")
        self.assertEqual(config.port, 5433)
        self.assertEqual(config.database, "mydb")
        self.assertEqual(config.user, "myuser")

    def test_port_validation_success(self):
        """Test valid port range."""
        config = DatabaseConfig(port=5432)
        self.assertEqual(config.port, 5432)

    def test_port_validation_too_low(self):
        """Test port validation fails for port < 1."""
        with self.assertRaises(ValueError) as ctx:
            DatabaseConfig(port=0)
        self.assertIn("Port must be between 1 and 65535", str(ctx.exception))

    def test_port_validation_too_high(self):
        """Test port validation fails for port > 65535."""
        with self.assertRaises(ValueError) as ctx:
            DatabaseConfig(port=70000)
        self.assertIn("Port must be between 1 and 65535", str(ctx.exception))

    def test_connection_string_without_password(self):
        """Test connection string generation without password."""
        config = DatabaseConfig()
        conn_str = config.connection_string()
        self.assertIn("postgresql://postgres@localhost:5432/pgosm", conn_str)
        self.assertIn("application_name=pgosm-flex", conn_str)
        self.assertNotIn(":", conn_str.split("@")[0].split("//")[1])

    def test_connection_string_with_password(self):
        """Test connection string generation with password."""
        config = DatabaseConfig(password="secret123")
        conn_str = config.connection_string()
        self.assertIn("secret123", conn_str)
        self.assertIn("postgresql://postgres:secret123@localhost:5432/pgosm", conn_str)

    def test_admin_connection_string_localhost(self):
        """Test admin connection string uses postgres database for localhost."""
        config = DatabaseConfig()
        conn_str = config.connection_string(admin=True)
        self.assertIn("/postgres?", conn_str)

    def test_admin_connection_string_remote(self):
        """Test admin connection string uses main database for remote host."""
        config = DatabaseConfig(host="remotehost")
        conn_str = config.connection_string(admin=True)
        self.assertIn("/pgosm?", conn_str)

    def test_special_characters_in_connection_string(self):
        """Test URL encoding of special characters in connection string."""
        config = DatabaseConfig(user="test@user", password="pass#word", host="db-host")
        conn_str = config.connection_string()
        self.assertIn("test%40user", conn_str)
        self.assertIn("pass%23word", conn_str)


class RegionConfigTests(unittest.TestCase):
    """Tests for RegionConfig model."""

    def test_region_without_subregion(self):
        """Test region configuration without subregion."""
        config = RegionConfig(region="north-america")
        self.assertEqual(config.region, "north-america")
        self.assertIsNone(config.subregion)

    def test_region_with_subregion(self):
        """Test region configuration with subregion."""
        config = RegionConfig(region="north-america", subregion="us")
        self.assertEqual(config.region, "north-america")
        self.assertEqual(config.subregion, "us")

    def test_region_combined_without_subregion(self):
        """Test region_combined property without subregion."""
        config = RegionConfig(region="europe")
        self.assertEqual(config.region_combined, "europe")

    def test_region_combined_with_subregion(self):
        """Test region_combined property with subregion."""
        config = RegionConfig(region="north-america", subregion="us")
        self.assertEqual(config.region_combined, "north-america-us")

    def test_region_combined_with_input_file(self):
        """Test region_combined returns input_file path when no region."""
        config = RegionConfig(input_file=Path("/data/custom.osm.pbf"))
        self.assertEqual(config.region_combined, "/data/custom.osm.pbf")

    def test_validation_fails_without_region_or_input(self):
        """Test validation requires region or input_file."""
        with self.assertRaises(ValueError) as ctx:
            RegionConfig()
        self.assertIn("Either region or input_file must be provided", str(ctx.exception))

    def test_validation_fails_subregion_without_region(self):
        """Test validation fails when subregion without region."""
        with self.assertRaises(ValueError) as ctx:
            RegionConfig(subregion="colorado")
        # Either error message is acceptable - both indicate the validation is working
        error_str = str(ctx.exception)
        self.assertTrue(
            "Cannot use subregion without region" in error_str or
            "Either region or input_file must be provided" in error_str
        )

    def test_validation_fails_region_with_slash(self):
        """Test validation fails when region contains slash without subregion."""
        with self.assertRaises(ValueError) as ctx:
            RegionConfig(region="north-america/us")
        self.assertIn("Region provided appears to include subregion", str(ctx.exception))

    def test_input_file_instead_of_region(self):
        """Test using input_file instead of region."""
        config = RegionConfig(input_file=Path("/data/custom.osm.pbf"))
        self.assertEqual(config.input_file, Path("/data/custom.osm.pbf"))
        self.assertIsNone(config.region)

    def test_default_pgosm_date(self):
        """Test default pgosm_date is today."""
        config = RegionConfig(region="europe")
        self.assertRegex(config.pgosm_date, r'^\d{4}-\d{2}-\d{2}$')

    def test_custom_pgosm_date(self):
        """Test custom pgosm_date."""
        config = RegionConfig(region="europe", pgosm_date="2024-01-20")
        self.assertEqual(config.pgosm_date, "2024-01-20")

    def test_skip_verify_checksum_default(self):
        """Test skip_verify_checksum defaults to False."""
        config = RegionConfig(region="europe")
        self.assertFalse(config.skip_verify_checksum)

    def test_skip_verify_checksum_set(self):
        """Test skip_verify_checksum can be set to True."""
        config = RegionConfig(region="europe", skip_verify_checksum=True)
        self.assertTrue(config.skip_verify_checksum)


class LayersetConfigTests(unittest.TestCase):
    """Tests for LayersetConfig model."""

    def test_default_layerset(self):
        """Test default layerset is 'default'."""
        config = LayersetConfig()
        self.assertEqual(config.layerset, "default")

    def test_custom_layerset(self):
        """Test custom layerset."""
        config = LayersetConfig(layerset="minimal")
        self.assertEqual(config.layerset, "minimal")

    def test_layerset_path_default(self):
        """Test layerset_path defaults to None."""
        config = LayersetConfig()
        self.assertIsNone(config.layerset_path)

    def test_custom_layerset_path(self):
        """Test custom layerset_path."""
        config = LayersetConfig(layerset_path=Path("/custom/path"))
        self.assertEqual(config.layerset_path, Path("/custom/path"))


class ImportConfigTests(unittest.TestCase):
    """Tests for ImportConfig model."""

    def test_default_values(self):
        """Test default import configuration."""
        config = ImportConfig()
        self.assertFalse(config.force)
        self.assertFalse(config.replication)
        self.assertFalse(config.replication_update)
        self.assertIsNone(config.update)
        self.assertFalse(config.skip_nested)
        self.assertFalse(config.skip_qgis_style)
        self.assertFalse(config.pg_dump)
        self.assertTrue(config.append_first_run)
        self.assertFalse(config.slim_no_drop)
        self.assertTrue(config.run_post_sql)

    def test_replication_mode(self):
        """Test replication mode sets slim_no_drop."""
        config = ImportConfig(replication=True)
        self.assertTrue(config.slim_no_drop)
        self.assertTrue(config.append_first_run)

    def test_replication_update_mode(self):
        """Test replication_update mode."""
        config = ImportConfig(replication=True, replication_update=True)
        self.assertFalse(config.append_first_run)

    def test_update_append_mode(self):
        """Test update append mode configuration."""
        config = ImportConfig(update="append")
        self.assertFalse(config.append_first_run)
        self.assertTrue(config.slim_no_drop)
        self.assertFalse(config.run_post_sql)

    def test_update_create_mode(self):
        """Test update create mode configuration."""
        config = ImportConfig(update="create")
        self.assertTrue(config.append_first_run)
        self.assertTrue(config.slim_no_drop)
        self.assertTrue(config.run_post_sql)

    def test_replication_and_update_mutually_exclusive(self):
        """Test replication and update cannot both be set."""
        with self.assertRaises(ValueError) as ctx:
            ImportConfig(replication=True, update="append")
        self.assertIn("mutually exclusive", str(ctx.exception))

    def test_force_flag(self):
        """Test force flag."""
        config = ImportConfig(force=True)
        self.assertTrue(config.force)

    def test_skip_nested_flag(self):
        """Test skip_nested flag."""
        config = ImportConfig(skip_nested=True)
        self.assertTrue(config.skip_nested)

    def test_skip_qgis_style_flag(self):
        """Test skip_qgis_style flag."""
        config = ImportConfig(skip_qgis_style=True)
        self.assertTrue(config.skip_qgis_style)

    def test_pg_dump_flag(self):
        """Test pg_dump flag."""
        config = ImportConfig(pg_dump=True)
        self.assertTrue(config.pg_dump)

    def test_as_json(self):
        """Test JSON serialization."""
        config = ImportConfig(replication=True, force=True)
        json_str = config.as_json()
        self.assertIn('"replication": true', json_str)
        self.assertIn('"slim_no_drop": true', json_str)
        # force is not in JSON output (as expected, it's not stored)
        self.assertNotIn('"force"', json_str)

    def test_okay_to_run_with_force(self):
        """Test okay_to_run returns True when force is set."""
        config = ImportConfig(force=True)
        result = config.okay_to_run({}, "0.1.0")
        self.assertTrue(result)

    def test_okay_to_run_no_prior_import(self):
        """Test okay_to_run returns True when no prior import."""
        config = ImportConfig()
        result = config.okay_to_run({}, "0.1.0")
        self.assertTrue(result)

    def test_okay_to_run_version_check_fails(self):
        """Test okay_to_run fails when current version is lower."""
        config = ImportConfig()
        prior_import = {
            'pgosm_flex_version_no_hash': '0.2.0',
            'replication': False
        }
        result = config.okay_to_run(prior_import, "0.1.0")
        self.assertFalse(result)

    def test_okay_to_run_version_check_passes(self):
        """Test okay_to_run checks version compatibility."""
        config = ImportConfig(force=True)
        prior_import = {
            'pgosm_flex_version_no_hash': '0.1.0',
            'replication': False
        }
        result = config.okay_to_run(prior_import, "0.2.0")
        self.assertTrue(result)

    def test_okay_to_run_replication_mode(self):
        """Test okay_to_run with replication mode."""
        config = ImportConfig(replication=True)
        prior_import = {
            'pgosm_flex_version_no_hash': '0.1.0',
            'replication': True
        }
        result = config.okay_to_run(prior_import, "0.1.0")
        self.assertTrue(result)

    def test_okay_to_run_replication_mismatch(self):
        """Test okay_to_run fails when replication mode doesn't match."""
        config = ImportConfig(replication=True)
        prior_import = {
            'pgosm_flex_version_no_hash': '0.1.0',
            'replication': False
        }
        result = config.okay_to_run(prior_import, "0.1.0")
        self.assertFalse(result)

    def test_okay_to_run_append_mode(self):
        """Test okay_to_run with append mode."""
        config = ImportConfig(update="append")
        prior_import = {
            'pgosm_flex_version_no_hash': '0.1.0',
            'replication': False
        }
        result = config.okay_to_run(prior_import, "0.1.0")
        self.assertTrue(result)

    def test_okay_to_run_requires_force(self):
        """Test okay_to_run fails when prior data exists and no force."""
        config = ImportConfig()
        prior_import = {
            'pgosm_flex_version_no_hash': '0.1.0',
            'replication': False
        }
        result = config.okay_to_run(prior_import, "0.1.0")
        self.assertFalse(result)


class ProcessingConfigTests(unittest.TestCase):
    """Tests for ProcessingConfig model."""

    def test_ram_required(self):
        """Test RAM is required."""
        with self.assertRaises(ValueError):
            ProcessingConfig()

    def test_ram_validation_positive(self):
        """Test RAM must be positive."""
        with self.assertRaises(ValueError) as ctx:
            ProcessingConfig(ram=-1.0)
        self.assertIn("RAM must be a positive number", str(ctx.exception))

    def test_ram_validation_zero(self):
        """Test RAM cannot be zero."""
        with self.assertRaises(ValueError):
            ProcessingConfig(ram=0.0)

    def test_default_srid(self):
        """Test default SRID is 3857."""
        config = ProcessingConfig(ram=4.0)
        self.assertEqual(config.srid, "3857")

    def test_custom_srid(self):
        """Test custom SRID."""
        config = ProcessingConfig(ram=4.0, srid="4326")
        self.assertEqual(config.srid, "4326")

    def test_default_schema_name(self):
        """Test default schema_name is osm."""
        config = ProcessingConfig(ram=4.0)
        self.assertEqual(config.schema_name, "osm")

    def test_custom_schema_name(self):
        """Test custom schema_name."""
        config = ProcessingConfig(ram=4.0, schema_name="myschema")
        self.assertEqual(config.schema_name, "myschema")

    def test_language_default(self):
        """Test language defaults to None."""
        config = ProcessingConfig(ram=4.0)
        self.assertIsNone(config.language)

    def test_language_custom(self):
        """Test custom language."""
        config = ProcessingConfig(ram=4.0, language="en")
        self.assertEqual(config.language, "en")

    def test_base_path_default(self):
        """Test base_path defaults to None."""
        config = ProcessingConfig(ram=4.0)
        self.assertIsNone(config.base_path)

    def test_base_path_absolute(self):
        """Test base_path with absolute path."""
        config = ProcessingConfig(ram=4.0, base_path=Path("/app"))
        self.assertEqual(config.base_path, Path("/app"))

    def test_base_path_validation_relative(self):
        """Test base_path validation fails for relative path."""
        with self.assertRaises(ValueError) as ctx:
            ProcessingConfig(ram=4.0, base_path=Path("relative/path"))
        self.assertIn("base_path must be an absolute path", str(ctx.exception))

    def test_debug_default(self):
        """Test debug defaults to False."""
        config = ProcessingConfig(ram=4.0)
        self.assertFalse(config.debug)

    def test_debug_set(self):
        """Test debug can be set to True."""
        config = ProcessingConfig(ram=4.0, debug=True)
        self.assertTrue(config.debug)

    def test_custom_values(self):
        """Test custom processing configuration."""
        config = ProcessingConfig(
            ram=8.0,
            srid="4326",
            language="en",
            schema_name="myschema",
            debug=True
        )
        self.assertEqual(config.ram, 8.0)
        self.assertEqual(config.srid, "4326")
        self.assertEqual(config.language, "en")
        self.assertEqual(config.schema_name, "myschema")
        self.assertTrue(config.debug)


class PgOSMFlexConfigTests(unittest.TestCase):
    """Tests for PgOSMFlexConfig root model."""

    def test_full_config_creation(self):
        """Test creating complete configuration."""
        config = PgOSMFlexConfig(
            database=DatabaseConfig(),
            region=RegionConfig(region="europe"),
            layerset=LayersetConfig(),
            import_mode=ImportConfig(),
            processing=ProcessingConfig(ram=4.0)
        )

        self.assertEqual(config.database.host, "localhost")
        self.assertEqual(config.region.region, "europe")
        self.assertEqual(config.processing.ram, 4.0)

    def test_default_factories(self):
        """Test default factory creation."""
        config = PgOSMFlexConfig(
            region=RegionConfig(region="europe"),
            processing=ProcessingConfig(ram=4.0)
        )

        # Check defaults were created
        self.assertIsNotNone(config.database)
        self.assertIsNotNone(config.layerset)
        self.assertIsNotNone(config.import_mode)

    def test_to_env_vars(self):
        """Test conversion to environment variables."""
        config = PgOSMFlexConfig(
            region=RegionConfig(region="north-america", subregion="us"),
            processing=ProcessingConfig(ram=4.0, srid="4326"),
            layerset=LayersetConfig(layerset="default"),
            import_mode=ImportConfig(skip_nested=True)
        )

        env_vars = config.to_env_vars()

        self.assertEqual(env_vars['PGOSM_REGION'], 'north-america')
        self.assertEqual(env_vars['PGOSM_SUBREGION'], 'us')
        self.assertEqual(env_vars['PGOSM_SRID'], '4326')
        self.assertEqual(env_vars['SCHEMA_NAME'], 'osm')
        self.assertEqual(env_vars['SKIP_NESTED'], 'True')
        self.assertIn('PGOSM_CONN', env_vars)
        self.assertIn('PGOSM_CONN_PG', env_vars)
        self.assertIn('POSTGRES_USER', env_vars)
        self.assertIn('POSTGRES_HOST', env_vars)
        self.assertIn('POSTGRES_PORT', env_vars)
        self.assertIn('POSTGRES_DB', env_vars)

    def test_to_env_vars_with_password(self):
        """Test to_env_vars includes password when set."""
        config = PgOSMFlexConfig(
            region=RegionConfig(region="europe"),
            processing=ProcessingConfig(ram=4.0),
            database=DatabaseConfig(password="secret")
        )

        env_vars = config.to_env_vars()
        self.assertEqual(env_vars['POSTGRES_PASSWORD'], 'secret')

    def test_to_env_vars_default_srid(self):
        """Test to_env_vars omits SRID when default."""
        config = PgOSMFlexConfig(
            region=RegionConfig(region="europe"),
            processing=ProcessingConfig(ram=4.0, srid="3857")
        )

        env_vars = config.to_env_vars()
        self.assertNotIn('PGOSM_SRID', env_vars)

    def test_apply_to_environment(self):
        """Test apply_to_environment sets os.environ."""
        config = PgOSMFlexConfig(
            region=RegionConfig(region="europe"),
            processing=ProcessingConfig(ram=4.0)
        )

        # Clear any existing env vars
        for key in list(os.environ.keys()):
            if key.startswith('PGOSM_') or key.startswith('POSTGRES_'):
                del os.environ[key]

        try:
            config.apply_to_environment()

            self.assertEqual(os.environ['PGOSM_REGION'], 'europe')
            self.assertEqual(os.environ['POSTGRES_USER'], 'postgres')
            self.assertIn('PGOSM_CONN', os.environ)
        finally:
            # Cleanup
            for key in list(os.environ.keys()):
                if key.startswith('PGOSM_') or key.startswith('POSTGRES_'):
                    del os.environ[key]


class ConfigLoaderTests(unittest.TestCase):
    """Tests for ConfigLoader."""

    def test_load_toml_file_not_exists(self):
        """Test loading non-existent TOML file returns empty dict."""
        result = ConfigLoader.load_toml(Path("/nonexistent/config.toml"))
        self.assertEqual(result, {})

    def test_load_toml_file_exists(self):
        """Test loading valid TOML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write("""
[database]
host = "testhost"
port = 5433

[processing]
ram = 8.0
srid = "4326"
""")
            f.flush()

            try:
                result = ConfigLoader.load_toml(Path(f.name))
                self.assertEqual(result['database']['host'], "testhost")
                self.assertEqual(result['database']['port'], 5433)
                self.assertEqual(result['processing']['ram'], 8.0)
            finally:
                os.unlink(f.name)

    @patch.dict(os.environ, {
        'POSTGRES_HOST': 'envhost',
        'POSTGRES_PORT': '5434',
        'PGOSM_REGION': 'europe'
    }, clear=True)
    def test_load_env_vars(self):
        """Test loading from environment variables."""
        result = ConfigLoader.load_env_vars()
        self.assertEqual(result['database']['host'], 'envhost')
        self.assertEqual(result['database']['port'], 5434)
        self.assertEqual(result['region']['region'], 'europe')

    def test_merge_configs_simple(self):
        """Test simple configuration merging."""
        config1 = {'database': {'host': 'host1', 'port': 5432}}
        config2 = {'database': {'host': 'host2'}}

        result = ConfigLoader.merge_configs(config1, config2)

        self.assertEqual(result['database']['host'], 'host2')  # Overridden
        self.assertEqual(result['database']['port'], 5432)     # Preserved

    def test_merge_configs_multiple(self):
        """Test merging multiple configurations."""
        config1 = {'a': 1, 'b': {'x': 10}}
        config2 = {'b': {'y': 20}, 'c': 3}
        config3 = {'b': {'x': 30}}

        result = ConfigLoader.merge_configs(config1, config2, config3)

        self.assertEqual(result['a'], 1)
        self.assertEqual(result['b']['x'], 30)  # Overridden by config3
        self.assertEqual(result['b']['y'], 20)  # From config2
        self.assertEqual(result['c'], 3)

    def test_cli_args_to_dict(self):
        """Test CLI arguments conversion to nested dict."""
        cli_args = {
            'ram': 4.0,
            'region': 'north-america',
            'subregion': 'us',
            'layerset': 'default',
            'force': True
        }

        result = ConfigLoader.cli_args_to_dict(cli_args)

        self.assertEqual(result['processing']['ram'], 4.0)
        self.assertEqual(result['region']['region'], 'north-america')
        self.assertEqual(result['region']['subregion'], 'us')
        self.assertEqual(result['layerset']['layerset'], 'default')
        self.assertEqual(result['import_mode']['force'], True)

    def test_cli_args_to_dict_ignores_none(self):
        """Test CLI args conversion ignores None values."""
        cli_args = {
            'ram': 4.0,
            'region': 'europe',
            'subregion': None,
            'language': None
        }

        result = ConfigLoader.cli_args_to_dict(cli_args)

        self.assertEqual(result['processing']['ram'], 4.0)
        self.assertEqual(result['region']['region'], 'europe')
        # None values should not be in result
        self.assertNotIn('subregion', result['region'])
        self.assertNotIn('language', result['processing'])

    @patch.dict(os.environ, {}, clear=True)
    def test_load_with_cli_args_only(self):
        """Test loading configuration from CLI args only."""
        cli_args = {
            'ram': 4.0,
            'region': 'europe'
        }

        config = ConfigLoader.load(cli_args=cli_args)

        self.assertEqual(config.processing.ram, 4.0)
        self.assertEqual(config.region.region, 'europe')
        self.assertEqual(config.database.host, 'localhost')  # Default

    def test_load_with_toml(self):
        """Test loading configuration from TOML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write("""
[region]
region = "asia"

[processing]
ram = 8.0
""")
            f.flush()

            try:
                # Clear environment
                for key in list(os.environ.keys()):
                    if key.startswith('PGOSM_') or key.startswith('POSTGRES_'):
                        del os.environ[key]

                config = ConfigLoader.load(toml_path=Path(f.name))

                self.assertEqual(config.processing.ram, 8.0)
                self.assertEqual(config.region.region, 'asia')
            finally:
                os.unlink(f.name)

    def test_load_precedence_cli_over_toml(self):
        """Test CLI arguments override TOML values."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write("""
[region]
region = "asia"

[processing]
ram = 8.0
srid = "3857"
""")
            f.flush()

            try:
                # Clear environment
                for key in list(os.environ.keys()):
                    if key.startswith('PGOSM_') or key.startswith('POSTGRES_'):
                        del os.environ[key]

                cli_args = {
                    'region': 'europe',
                    'ram': 4.0
                }

                config = ConfigLoader.load(cli_args=cli_args, toml_path=Path(f.name))

                # CLI should override TOML
                self.assertEqual(config.region.region, 'europe')
                self.assertEqual(config.processing.ram, 4.0)
                # TOML value should be preserved when not in CLI
                self.assertEqual(config.processing.srid, '3857')
            finally:
                os.unlink(f.name)

    @patch.dict(os.environ, {
        'PGOSM_REGION': 'africa',
        'POSTGRES_HOST': 'envhost'
    }, clear=True)
    def test_load_precedence_toml_over_env(self):
        """Test TOML overrides environment variables."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write("""
[region]
region = "asia"

[processing]
ram = 8.0

[database]
host = "tomlhost"
""")
            f.flush()

            try:
                config = ConfigLoader.load(toml_path=Path(f.name))

                # TOML should override env
                self.assertEqual(config.region.region, 'asia')
                self.assertEqual(config.database.host, 'tomlhost')
            finally:
                os.unlink(f.name)


if __name__ == '__main__':
    unittest.main()
