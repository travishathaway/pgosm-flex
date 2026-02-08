"""
Configuration management for PgOSM Flex using Pydantic.

This module provides type-safe configuration with automatic validation,
supporting multiple configuration sources with clear precedence:
CLI args > TOML file > Environment variables > Defaults
"""

import contextlib
import datetime
import json
import logging
import os
from contextvars import ContextVar
from importlib import resources
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

import osmium
from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import SettingsConfigDict

_config_context: ContextVar["PgOSMFlexConfig | None"] = ContextVar("config", default=None)


def get_config() -> "PgOSMFlexConfig":
    """Get PgOSM Flex configuration."""
    config = _config_context.get()
    if config is None:
        msg = "Configuration is not initialized"
        raise RuntimeError(msg)
    return config


def init_config(
    cli_args: dict | None = None, toml_path: Path = Path("pgosm-flex.toml")
) -> "PgOSMFlexConfig":
    """Initialize configuration in current context."""
    config = ConfigLoader.load(cli_args=cli_args, toml_path=toml_path)
    _config_context.set(config)
    return config


@contextlib.contextmanager
def config_context(config: "PgOSMFlexConfig"):
    """Context manager for testing with different configs."""
    token = _config_context.set(config)
    try:
        yield config
    finally:
        _config_context.reset(token)


def get_today() -> str:
    """Returns yyyy-mm-dd formatted string for today.

    Returns
    -------
    today : str
    """
    return datetime.datetime.today().strftime("%Y-%m-%d")


class DatabaseConfig(BaseModel):
    """PostgreSQL database connection configuration.

    Maps to POSTGRES_* environment variables.
    """

    host: str = "localhost"
    port: int = 5432
    database: str = "pgosm"
    user: str = "postgres"
    password: SecretStr | None = None

    model_config = SettingsConfigDict(env_prefix="POSTGRES_", case_sensitive=False)

    @field_validator("port")
    @classmethod
    def validate_port(cls, v):
        """Validate port is in valid range."""
        if not 1 <= v <= 65535:
            msg = "Port must be between 1 and 65535"
            raise ValueError(msg)
        return v

    def connection_string(self, admin: bool = False) -> str:
        """Build PostgreSQL connection URI.

        Mirrors logic from db.connection_string().

        Parameters
        ----------
        admin : bool
            Connect to admin database (postgres) instead of main database

        Returns
        -------
        str
            PostgreSQL connection URI
        """
        user = quote(self.user)
        host = quote(self.host)
        port = str(self.port)

        if admin:
            db_name = "postgres" if self.host == "localhost" else self.database
        else:
            db_name = self.database

        db_name = quote(db_name)
        app_str = "?application_name=pgosm-flex"

        if self.password is None:
            return f"postgresql://{user}@{host}:{port}/{db_name}{app_str}"
        password = quote(self.password.get_secret_value())
        return f"postgresql://{user}:{password}@{host}:{port}/{db_name}{app_str}"


class RegionConfig(BaseModel):
    """Region and OSM data source configuration."""

    region: str | None = None
    subregion: str | None = None
    input_file: Path | None = None
    pgosm_date: str | None = None
    skip_verify_checksum: bool = False

    @field_validator("input_file", mode="before")
    @classmethod
    def convert_input_file(cls, v):
        """Convert string input_file to Path if needed."""
        if v is None or isinstance(v, Path):
            return v
        return Path(v)

    @model_validator(mode="after")
    def validate_region_or_input(self):
        """Ensure either region or input_file is provided.

        Mirrors validation from main.validate_region_inputs().
        """
        if self.region is None and self.input_file is None:
            msg = "Either region or input_file must be provided"
            raise ValueError(msg)

        if self.region is None and self.subregion is not None:
            msg = "Cannot use subregion without region"
            raise ValueError(msg)

        if self.region is not None and "/" in self.region and self.subregion is None:
            msg = (
                "Region provided appears to include subregion. "
                "Use --subregion to specify subregion separately."
            )
            raise ValueError(msg)

        if self.input_file is not None and not self.input_file.is_file():
            msg = "Input file does not exist"
            raise ValueError(msg)

        return self

    @property
    def region_combined(self) -> str:
        """Returns combined region-subregion string.

        Mirrors logic from helpers.get_region_combined().

        Returns
        -------
        str
            Combined region string (region or region-subregion or input_file)
        """
        if self.subregion is None:
            return self.region or str(self.input_file)
        return f"{self.region}-{self.subregion}"

    @property
    def input_file_str(self) -> str | None:
        """Returns input_file as string or None.

        Useful for compatibility with code expecting string paths.

        Returns
        -------
        Optional[str]
            Input file path as string, or None
        """
        return str(self.input_file) if self.input_file else None

    @model_validator(mode="before")
    @classmethod
    def set_pgosm_date(cls, data):
        """
        Set pgosm date based on the input_file field or default to today.
        """
        if input_file := data.get("input_file"):
            if os.path.isfile(input_file):
                try:
                    reader = osmium.io.Reader(input_file)
                    header = reader.header()
                    pgosm_datetime = datetime.datetime.strptime(
                        header.get("osmosis_replication_timestamp"), "%Y-%m-%dT%H:%M:%SZ"
                    )
                    data["pgosm_date"] = pgosm_datetime.strftime("%Y-%m-%d")
                except RuntimeError as err:
                    raise ValueError("Error parsing pgosm date file input_file") from err

        elif data.get("pgosm_date") is None:
            data["pgosm_date"] = get_today()

        return data


class LayersetConfig(BaseModel):
    """Layerset configuration for OSM data layers."""

    layerset: str = "default"
    layerset_path: Path | None = None

    def load_layerset_ini(self, flex_path: Path) -> dict:
        """Load and parse layerset INI file.

        Mirrors logic from main.layerset_include_place().

        Parameters
        ----------
        flex_path : Path
            Base path to flex-config directory

        Returns
        -------
        dict
            Parsed layerset configuration
        """
        import configparser

        if self.layerset_path is None:
            ini_path = flex_path / "layerset" / f"{self.layerset}.ini"
        else:
            ini_path = self.layerset_path / f"{self.layerset}.ini"

        config = configparser.ConfigParser()
        config.read(ini_path)

        return dict(config["layerset"])


class ImportConfig(BaseModel):
    """Import mode configuration."""

    # Input flags
    force: bool = False
    replication: bool = False
    replication_update: bool = False
    update: Literal["append", "create"] | None = None
    skip_nested: bool = False
    skip_qgis_style: bool = False
    pg_dump: bool = False

    # Computed flags (set by validator)
    slim_no_drop: bool = False
    append_first_run: bool = True
    run_post_sql: bool = True

    @model_validator(mode="after")
    def validate_and_compute(self):
        """Validate mutual exclusivity and compute derived flags.

        Mirrors logic from ImportMode.__init__() and set_* methods.
        """
        # Validate mutual exclusivity
        if self.replication and self.update is not None:
            msg = (
                "The --replication and --update features are mutually exclusive. "
                "Use one or the other."
            )
            raise ValueError(msg)

        # Compute slim_no_drop (from set_slim_no_drop)
        self.slim_no_drop = self.replication or (self.update is not None)

        # Compute append_first_run (from set_append_first_run)
        if self.replication_update:
            self.append_first_run = False
        elif self.update == "create":
            self.append_first_run = True
        elif self.update == "append":
            self.append_first_run = False
        else:
            self.append_first_run = True

        # Compute run_post_sql (from set_run_post_sql)
        self.run_post_sql = self.update != "append"

        return self

    def okay_to_run(self, prior_import: dict, current_version: str) -> bool:
        """Determine if it's safe to run without data loss.

        Mirrors logic from ImportMode.okay_to_run()

        Parameters
        ----------
        prior_import : dict
            Details about the latest import from osm.pgosm_flex table.
            An empty dictionary (len==0) indicates no prior import.
        current_version : str
            Current PgOSM Flex version

        Returns
        -------
        bool
            True if it's safe to run, False otherwise
        """
        from packaging.version import parse as parse_version

        logger = logging.getLogger("pgosm-flex")
        logger.debug("Checking if it is okay to run...")

        if self.force:
            logger.warning("Using --force, kiss existing data goodbye.")
            return True

        # No prior imports - safe to proceed
        if len(prior_import) == 0:
            logger.debug("No prior import found, okay to proceed.")
            return True

        # Check version compatibility
        prior_version = prior_import["pgosm_flex_version_no_hash"]
        if parse_version(current_version) < parse_version(prior_version):
            msg = f"PgOSM Flex version ({current_version}) is lower than latest import"
            msg += f" tracked in the pgosm_flex table ({prior_version})."
            msg += f" Use PgOSM Flex version {prior_version} or newer"
            logger.error(msg)
            return False
        logger.info(f"Prior import used PgOSM Flex: {prior_version}")

        # Check replication compatibility
        prior_replication = prior_import["replication"]
        if self.replication:
            if not prior_replication:
                logger.error(
                    "Running w/ replication but prior import did not. Requires --force to proceed."
                )
                return False
            logger.debug("Okay to proceed with replication")
            return True

        # Allow append mode
        if self.update == "append":
            return True

        # Default: require --force if prior data exists
        msg = "Prior data exists in the osm schema and --force was not used."
        logger.error(msg)
        return False

    def as_json(self) -> str:
        """Export as JSON string for database storage.

        Mirrors ImportMode.as_json() (lines 351-365).

        Returns
        -------
        str
            JSON string representation of import configuration
        """
        return json.dumps(
            {
                "update": self.update,
                "replication": self.replication,
                "replication_update": self.replication_update,
                "append_first_run": self.append_first_run,
                "slim_no_drop": self.slim_no_drop,
                "run_post_sql": self.run_post_sql,
            }
        )


class ProcessingConfig(BaseModel):
    """Processing configuration for osm2pgsql and data handling."""

    ram: float  # Required - amount of RAM in GB
    srid: str = "3857"  # helpers.DEFAULT_SRID
    language: str = "en"
    schema_name: str = "osm"
    base_path: Path | None = Field(default_factory=lambda: Path(str(resources.files("pgosm_flex"))))
    data_dir: Path | None = None  # Override data directory
    debug: bool = False

    @field_validator("ram")
    @classmethod
    def validate_ram(cls, v):
        """Validate RAM is positive."""
        if v <= 0:
            msg = "RAM must be a positive number"
            raise ValueError(msg)
        return v

    @field_validator("base_path")
    @classmethod
    def validate_base_path(cls, v):
        """Validate base_path is absolute if provided."""
        if v is not None:
            path = Path(v)
            if not path.is_absolute():
                msg = "base_path must be an absolute path"
                raise ValueError(msg)
        return v

    @field_validator("data_dir")
    @classmethod
    def validate_data_dir(cls, v):
        """Validate data_dir is absolute if provided."""
        if v is not None:
            path = Path(v)
            if not path.is_absolute():
                msg = "data_dir must be an absolute path"
                raise ValueError(msg)
        return v


class PgOSMFlexConfig(BaseModel):
    """Root configuration for PgOSM Flex.

    Consolidates all configuration from CLI, TOML, and environment variables.
    """

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    region: RegionConfig = Field(default_factory=RegionConfig)
    layerset: LayersetConfig = Field(default_factory=LayersetConfig)
    import_mode: ImportConfig = Field(default_factory=ImportConfig)
    processing: ProcessingConfig

    model_config = SettingsConfigDict(
        env_prefix="PGOSM_", env_nested_delimiter="__", extra="forbid"
    )

    def to_env_vars(self) -> dict[str, str]:
        """Convert configuration to environment variable dict.

        Used for backward compatibility during migration.
        Mirrors logic from helpers.set_env_vars().

        Returns
        -------
        dict[str, str]
            Dictionary of environment variables
        """
        env = {}

        # Region settings
        if self.region.region:
            env["PGOSM_REGION"] = self.region.region
        if self.region.subregion:
            env["PGOSM_SUBREGION"] = self.region.subregion
        if self.processing.srid != "3857":
            env["PGOSM_SRID"] = self.processing.srid
        if self.processing.language:
            env["PGOSM_LANGUAGE"] = self.processing.language

        env["PGOSM_DATE"] = self.region.pgosm_date
        env["PGOSM_LAYERSET"] = self.layerset.layerset

        if self.layerset.layerset_path:
            env["PGOSM_LAYERSET_PATH"] = str(self.layerset.layerset_path)

        env["SCHEMA_NAME"] = self.processing.schema_name
        env["SKIP_NESTED"] = str(self.import_mode.skip_nested)

        # Database connections
        env["PGOSM_CONN"] = self.database.connection_string()
        env["PGOSM_CONN_PG"] = self.database.connection_string(admin=True)

        # PostgreSQL variables
        env["POSTGRES_USER"] = self.database.user
        env["POSTGRES_HOST"] = self.database.host
        env["POSTGRES_PORT"] = str(self.database.port)
        env["POSTGRES_DB"] = self.database.database
        if self.database.password:
            env["POSTGRES_PASSWORD"] = self.database.password.get_secret_value()

        return env

    def apply_to_environment(self):
        """Apply configuration to os.environ (backward compatibility bridge)."""
        for key, value in self.to_env_vars().items():
            os.environ[key] = value


class ConfigLoader:
    """Loads configuration from multiple sources with proper precedence."""

    @staticmethod
    def load_toml(path: Path = Path("pgosm-flex.toml")) -> dict:
        """Load TOML configuration file if it exists.

        Parameters
        ----------
        path : Path
            Path to TOML configuration file

        Returns
        -------
        dict
            Parsed TOML configuration, or empty dict if file doesn't exist
        """
        if not path.exists():
            return {}

        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]  # Fallback for Python 3.10

        with open(path, "rb") as f:
            return tomllib.load(f)

    @staticmethod
    def load_env_vars() -> dict:
        """Load configuration from environment variables.

        Returns a nested dict structure matching the config model.

        Returns
        -------
        dict
            Nested configuration dictionary from environment variables
        """
        config: dict[str, dict[str, Any]] = {
            "database": {},
            "region": {},
            "layerset": {},
            "import_mode": {},
            "processing": {},
        }

        # Database config
        if "POSTGRES_HOST" in os.environ:
            config["database"]["host"] = os.environ["POSTGRES_HOST"]
        if "POSTGRES_PORT" in os.environ:
            config["database"]["port"] = int(os.environ["POSTGRES_PORT"])
        if "POSTGRES_DB" in os.environ:
            config["database"]["database"] = os.environ["POSTGRES_DB"]
        if "POSTGRES_USER" in os.environ:
            config["database"]["user"] = os.environ["POSTGRES_USER"]
        if "POSTGRES_PASSWORD" in os.environ:
            config["database"]["password"] = os.environ["POSTGRES_PASSWORD"]

        # Region config
        if "PGOSM_REGION" in os.environ:
            config["region"]["region"] = os.environ["PGOSM_REGION"]
        if "PGOSM_SUBREGION" in os.environ:
            config["region"]["subregion"] = os.environ["PGOSM_SUBREGION"]
        if "PGOSM_DATE" in os.environ:
            config["region"]["pgosm_date"] = os.environ["PGOSM_DATE"]

        # Layerset config
        if "PGOSM_LAYERSET" in os.environ:
            config["layerset"]["layerset"] = os.environ["PGOSM_LAYERSET"]
        if "PGOSM_LAYERSET_PATH" in os.environ:
            config["layerset"]["layerset_path"] = os.environ["PGOSM_LAYERSET_PATH"]

        # Processing config
        if "PGOSM_SRID" in os.environ:
            config["processing"]["srid"] = os.environ["PGOSM_SRID"]
        if "PGOSM_LANGUAGE" in os.environ:
            config["processing"]["language"] = os.environ["PGOSM_LANGUAGE"]
        if "SCHEMA_NAME" in os.environ:
            config["processing"]["schema_name"] = os.environ["SCHEMA_NAME"]

        # Import mode config
        if "SKIP_NESTED" in os.environ:
            config["import_mode"]["skip_nested"] = os.environ["SKIP_NESTED"].lower() == "true"

        return config

    @staticmethod
    def merge_configs(*configs: dict) -> dict:
        """Deep merge configurations (later configs override earlier ones).

        Parameters
        ----------
        *configs : dict
            Variable number of configuration dictionaries to merge

        Returns
        -------
        dict
            Merged configuration dictionary
        """
        result: dict[str, Any] = {}

        for config in configs:
            for key, value in config.items():
                if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                    # Recursively merge nested dicts
                    result[key] = ConfigLoader.merge_configs(result[key], value)
                else:
                    # Override with new value
                    result[key] = value

        return result

    @classmethod
    def load(
        cls, cli_args: dict | None = None, toml_path: Path = Path("pgosm-flex.toml")
    ) -> PgOSMFlexConfig:
        """Load configuration with precedence: CLI > TOML > Env > Defaults.

        Parameters
        ----------
        cli_args : dict, optional
            Arguments from Click CLI
        toml_path : Path
            Path to TOML configuration file (default: ./pgosm-flex.toml)

        Returns
        -------
        PgOSMFlexConfig
            Fully loaded and validated configuration
        """
        logger = logging.getLogger("pgosm-flex")

        # Load from each source
        env_config = cls.load_env_vars()
        logger.debug(f"Loaded env config: {len(env_config)} sections")

        toml_config = cls.load_toml(toml_path)
        if toml_config:
            logger.info(f"Loaded TOML config from {toml_path}")

        cli_config = cls.cli_args_to_dict(cli_args) if cli_args else {}

        # Merge with precedence: defaults < env < toml < cli
        merged = cls.merge_configs(env_config, toml_config, cli_config)

        # Create and validate config object
        try:
            config = PgOSMFlexConfig(**merged)
            logger.debug("Configuration validated successfully")
            return config
        except Exception as e:
            logger.exception(f"Configuration validation failed: {e}")
            raise

    @staticmethod
    def cli_args_to_dict(cli_args: dict) -> dict:
        """Convert flat CLI arguments to nested config structure.

        Parameters
        ----------
        cli_args : dict
            Flat dictionary of CLI arguments

        Returns
        -------
        dict
            Nested configuration dictionary
        """
        config: dict[str, dict[str, Any]] = {
            "database": {},
            "region": {},
            "layerset": {},
            "import_mode": {},
            "processing": {},
        }

        # Map CLI args to config sections
        mapping = {
            "pg_user": ("database", "user"),
            "pg_dbname": ("database", "database"),
            "pg_host": ("database", "host"),
            "pg_port": ("database", "port"),
            "pg_password": ("database", "password"),
            "region": ("region", "region"),
            "subregion": ("region", "subregion"),
            "input_file": ("region", "input_file"),
            "pgosm_date": ("region", "pgosm_date"),
            "skip_verify_checksum": ("region", "skip_verify_checksum"),
            "layerset": ("layerset", "layerset"),
            "layerset_path": ("layerset", "layerset_path"),
            "force": ("import_mode", "force"),
            "replication": ("import_mode", "replication"),
            "update": ("import_mode", "update"),
            "skip_nested": ("import_mode", "skip_nested"),
            "skip_qgis_style": ("import_mode", "skip_qgis_style"),
            "pg_dump": ("import_mode", "pg_dump"),
            "ram": ("processing", "ram"),
            "srid": ("processing", "srid"),
            "language": ("processing", "language"),
            "schema_name": ("processing", "schema_name"),
            "base_path": ("processing", "base_path"),
            "data_dir": ("processing", "data_dir"),
            "debug": ("processing", "debug"),
        }

        for cli_key, (section, config_key) in mapping.items():
            if cli_key in cli_args and cli_args[cli_key] is not None:
                config[section][config_key] = cli_args[cli_key]

        return config
