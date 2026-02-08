"""
pgosm-flex, an OpenStreetMap data import tool for PostgreSQL/PostGIS.

Documentation available at https://pgosm-flex.com/
"""

import configparser
import contextlib
import io
import logging
import os
import sys
from importlib import resources
from pathlib import Path
from tempfile import NamedTemporaryFile

import click

from pgosm_flex import __version__, db, geofabrik, helpers
from pgosm_flex import osm2pgsql_recommendation as rec
from pgosm_flex.config import get_config, init_config


@click.command()
# Required and most common options first
@click.option(
    "--ram",
    required=False,
    type=float,
    help="Amount of RAM in GB available on the machine running the Docker container. This is used to determine the "
    "appropriate osm2pgsql command via osm2pgsql-tuner recommendation engine.",
)
@click.option(
    "--region",
    required=False,
    help="Region name matching the filename for data sourced from Geofabrik. e.g. north-america/us. Optional when "
    "--input-file is specified, otherwise required.",
)
@click.option(
    "--subregion",
    required=False,
    help="Sub-region name matching the filename for data sourced from Geofabrik. e.g. district-of-columbia",
)
# Remainder of options in alphabetical order
@click.option("--debug", is_flag=True, help="Enables additional log output")
@click.option(
    "--force",
    is_flag=True,
    help="Danger!  Forces PgOSM Flex to load the data even if this will overwrite pre-existing data. See "
    "https://pgosm-flex.com/force-load.html for more.",
)
@click.option(
    "--input-file",
    required=False,
    default=None,
    help="Set filename or absolute filepath to input osm.pbf file. Overrides default file handling, archiving, "
    "and MD5 checksum validation.",
)
@click.option(
    "--layerset",
    required=False,
    default="default",
    help="Layerset to load. Defines name of included layerset unless --layerset-path is defined.",
)
@click.option("--layerset-path", required=False, help="Custom path to load layerset INI from.")
@click.option(
    "--language",
    default=None,
    envvar="PGOSM_LANGUAGE",
    help="Set default language in loaded OpenStreetMap data when available.  e.g. 'en' or 'kn'.",
)
@click.option(
    "--pg-dump",
    default=False,
    is_flag=True,
    help="Uses pg_dump after processing is completed to enable easily load OpenStreetMap data into a different database",
)
@click.option(
    "--pgosm-date",
    required=False,
    default=helpers.get_today(),
    envvar="PGOSM_DATE",
    help="Date of the data in YYYY-MM-DD format. If today (default), automatically downloads when files not found "
    "locally. Set to historic date to load locally archived PBF/MD5 file, will fail if both files do not exist.",
)
@click.option(
    "--replication",
    default=False,
    is_flag=True,
    help="Replication mode enables updates via osm2pgsql-replication.",
)
@click.option(
    "--schema-name", default="osm", help="Schema name to load OpenStreetMap data into.  Default osm"
)
@click.option(
    "--skip-nested",
    default=False,
    is_flag=True,
    help="When set, skips calculating nested admin polygons. Can be time consuming on large regions.",
)
@click.option(
    "--skip-qgis-style",
    default=False,
    is_flag=True,
    help="When set, skips running importing QGIS Styles.",
)
@click.option(
    "--skip-verify-checksum",
    default=False,
    is_flag=True,
    help="When set, skips verifying the md5 checksum from Geofabrik",
)
@click.option(
    "--srid",
    required=False,
    default=helpers.DEFAULT_SRID,
    envvar="PGOSM_SRID",
    help=f"SRID for data loaded by osm2pgsql to PostGIS. Defaults to SRID {helpers.DEFAULT_SRID}.",
)
@click.option(
    "--update",
    default=None,
    type=click.Choice(["append", "create"], case_sensitive=True),
    help="EXPERIMENTAL - Wrap around osm2pgsql create v. append modes, without using osm2pgsql-replication.",
)
@click.option(
    "--base-path",
    default=None,
    help='base path containing files necessary for import. default "/app"',
)
@click.option(
    "--data-dir",
    default=None,
    type=click.Path(path_type=Path),
    help="Directory for downloaded OSM data files. Defaults to platform-specific cache directory.",
)
@click.option(
    "--db-host",
    "--pg-host",
    "pg_host",
    default=None,
    envvar="POSTGRES_HOST",
    help="PostgreSQL host. Defaults to localhost",
)
@click.option(
    "--db-port",
    "--pg-port",
    "pg_port",
    default=None,
    type=int,
    envvar="POSTGRES_PORT",
    help="PostgreSQL port. Defaults to 5432",
)
@click.option(
    "--db-name",
    "--pg-dbname",
    "pg_dbname",
    default=None,
    envvar="POSTGRES_DB",
    help="PostgreSQL database name. Defaults to pgosm",
)
@click.option(
    "--db-user",
    "--pg-user",
    "pg_user",
    default=None,
    envvar="POSTGRES_USER",
    help="PostgreSQL user. Defaults to postgres",
)
@click.option(
    "--db-password",
    "--pg-password",
    "pg_password",
    default=None,
    envvar="POSTGRES_PASSWORD",
    help="PostgreSQL password. Optional.",
)
def run_pgosm_flex(
    ram,
    region,
    subregion,
    debug,
    force,
    input_file,
    layerset,
    layerset_path,
    language,
    pg_dump,
    pgosm_date,
    replication,
    schema_name,
    skip_nested,
    skip_qgis_style,
    srid,
    update,
    base_path,
    data_dir,
    skip_verify_checksum,
    pg_host,
    pg_port,
    pg_dbname,
    pg_user,
    pg_password,
):
    """Run PgOSM Flex to automate osm2pgsql flex processing."""
    # Collect CLI args into dict
    cli_args = {
        "ram": ram,
        "region": region,
        "subregion": subregion,
        "debug": debug,
        "force": force,
        "input_file": input_file,
        "layerset": layerset,
        "layerset_path": layerset_path,
        "language": language,
        "pg_dump": pg_dump,
        "pgosm_date": pgosm_date,
        "replication": replication,
        "schema_name": schema_name,
        "skip_nested": skip_nested,
        "skip_qgis_style": skip_qgis_style,
        "srid": srid,
        "update": update,
        "base_path": base_path,
        "data_dir": data_dir,
        "skip_verify_checksum": skip_verify_checksum,
        "pg_host": pg_host,
        "pg_port": pg_port,
        "pg_dbname": pg_dbname,
        "pg_user": pg_user,
        "pg_password": pg_password,
    }

    # Load configuration with precedence: CLI > TOML > Env > Defaults
    try:
        config = init_config(cli_args)
    except ValueError as e:
        logger = logging.getLogger("pgosm-flex")
        logger.exception(f"Configuration error: {e}")
        sys.exit(1)

    # Setup paths and logging
    paths = get_paths()
    setup_logger(config.processing.debug)
    logger = logging.getLogger("pgosm-flex")
    logger.info("PgOSM Flex starting...")

    # Use config values throughout
    db.wait_for_postgres()

    if config.import_mode.replication:
        replication_update = check_replication_exists()
        if replication_update and config.import_mode.force:
            err_msg = "Using --force is invalid when --replication is running an update."
            err_msg += " See https://pgosm-flex.com/replication.html#resetting-replication"
            err_msg += " for instructions around this on a development server."
            logger.error(err_msg)
            sys.exit(f"ERROR: {err_msg}")
        # Update config with replication_update status
        config.import_mode.replication_update = replication_update
    else:
        replication_update = False

    # Setting pgosm_date when replication is updating isn't an option
    if replication_update and config.region.pgosm_date != helpers.get_today():
        logger.warning("Overriding --pgosm-date due to replication update mode, setting to today")
        config.region.pgosm_date = helpers.get_today()

    logger.debug(f"UPDATE setting:  {config.import_mode.update}")

    db.prepare_pgosm_db(db_path=paths["db_path"])

    prior_import = db.get_prior_import(schema_name=config.processing.schema_name)

    if not config.import_mode.okay_to_run(prior_import, __version__):
        msg = "Not okay to run PgOSM Flex. Exiting"
        logger.error(msg)
        sys.exit(msg)

    # There's probably a better way to get this data out, but this worked right
    # away and I'm moving on.  I'm breaking enough other things that this seemed
    # to be a good compromise today.
    vers_lines = []
    helpers.run_command_via_subprocess(
        cmd=["osm2pgsql", "--version"], cwd="/usr/bin/", output_lines=vers_lines
    )

    import_id = db.start_import(
        osm2pgsql_version=vers_lines, schema_name=config.processing.schema_name
    )

    logger.info(f"Started import id {import_id}")

    if config.import_mode.replication_update:
        logger.info("Running osm2pgsql-replication in update mode")
        success = run_replication_update(
            skip_nested=config.import_mode.skip_nested, flex_path=paths["flex_path"]
        )
    else:
        logger.info("Running osm2pgsql")
        success = run_osm2pgsql_standard(
            input_file=config.region.input_file_str,
            out_path=paths["out_path"],
            flex_path=paths["flex_path"],
            skip_nested=config.import_mode.skip_nested,
            import_mode=config.import_mode,
            debug=config.processing.debug,
        )

    if not success:
        msg = "PgOSM Flex completed with errors. Details in output"
        db.log_import_message(
            import_id=import_id, msg="Failed", schema_name=config.processing.schema_name
        )
        logger.warning(msg)
        sys.exit(msg)

    db.log_import_message(
        import_id=import_id, msg="Completed", schema_name=config.processing.schema_name
    )

    dump_database(
        input_file=config.region.input_file_str,
        out_path=paths["out_path"],
        pg_dump=config.import_mode.pg_dump,
        skip_qgis_style=config.import_mode.skip_qgis_style,
    )

    logger.info("PgOSM Flex complete!")


def run_osm2pgsql_standard(input_file, out_path, flex_path, skip_nested, import_mode, debug):
    """Runs standard osm2pgsql command and optionally inits for replication
    (osm2pgsql-replication) mode.

    Parameters
    ----------
    input_file : str
    out_path : str
    flex_path : str
    skip_nested : boolean
    import_mode : helpers.helpers.ImportMode
    debug : boolean

    Returns
    -------
    post_processing : boolean
        Indicates overall success/failure of the steps within this function.
    """
    logger = logging.getLogger("pgosm-flex")
    config = get_config()

    if config.region.input_file is None:
        pbf_filename = geofabrik.prepare_data(out_path=out_path, skip_verify_checksum=True)
    else:
        pbf_filename = config.region.input_file

    # Generate Lua configuration module first
    with generate_lua_config() as lua_config_path:
        # Then generate Lua style file
        with lua_style() as tmp_lua_style:
            osm2pgsql_command = rec.osm2pgsql_recommendation(
                ram=config.processing.ram,
                pbf_filename=pbf_filename,
                out_path=out_path,
                import_mode=config.import_mode,
                pgosm_layer_set=tmp_lua_style.name,
            )

            run_osm2pgsql(osm2pgsql_command=osm2pgsql_command, flex_path=flex_path, debug=debug)

    if not skip_nested:
        # Don't expect user to use --skip-nested when place isn't included
        skip_nested = check_layerset_skip_nested_place(flex_path)

    post_processing = run_post_processing(flex_path=flex_path, skip_nested=skip_nested)

    if import_mode.replication:
        run_osm2pgsql_replication_init(pbf_path=out_path, pbf_filename=pbf_filename)
    else:
        logger.debug("Not using replication mode")

    if input_file is None:
        geofabrik.remove_latest_files(out_path)

    return post_processing


@contextlib.contextmanager
def lua_style():
    """
    Reads the layerset configuration and creates a temp lua style file for
    osm2pgsql-replication to use.

    Returns
    -------

    """
    config = get_config()
    paths = get_paths()

    with NamedTemporaryFile(mode="w", delete=True, suffix=".lua") as tmp_lua_style:
        style_config = config.layerset.load_layerset_ini(paths["flex_path"])

        for key, value in style_config.items():
            if value.lower() == "true":
                tmp_lua_style.write(f"print('Including {key}')\n")
                tmp_lua_style.write(f'require "style.{key}"\n')

        tmp_lua_style.flush()

        yield tmp_lua_style


def _write_index_config(file_handle, flex_path: Path, layer_name: str) -> None:
    """Helper to write index configuration for a layer to Lua format.

    Parameters
    ----------
    file_handle : file object
        Open file handle to write to
    flex_path : Path
        Path to flex-config directory containing indexes/
    layer_name : str
        Name of the layer (e.g., 'poi', 'building')
    """
    index_file = flex_path / "indexes" / f"{layer_name}.ini"

    if not index_file.exists():
        # No index config - write empty config
        file_handle.write("{}")
        return

    config = configparser.ConfigParser()
    config.read(index_file)

    file_handle.write("{\n")

    # Write each geometry type section
    for section in ["point", "line", "polygon", "all"]:
        if section in config:
            file_handle.write(f"            {section} = {{\n")
            for key, value in config[section].items():
                # Convert string boolean to Lua boolean, handle other types
                if value.lower() in ["true", "false"]:
                    lua_value = value.lower()
                else:
                    # Quote string values
                    lua_value = f"'{value}'"
                file_handle.write(f"                {key} = {lua_value},\n")
            file_handle.write("            },\n")

    file_handle.write("        }")


@contextlib.contextmanager
def generate_lua_config():
    """
    Generates temporary Lua configuration module with all config values.

    Replaces INI file parsing and environment variable reading in Lua scripts.
    Creates a pgosm_config.lua module in the flex_path directory that exports
    a configuration table with:
    - Core config (srid, schema_name, pgosm_date, language)
    - Enabled layers (from layerset INI)
    - Index specifications (from indexes/*.ini files)

    Yields
    ------
    str
        Path to generated pgosm_config.lua module
    """
    config = get_config()
    paths = get_paths()
    flex_path = paths["flex_path"]

    tmp_config = io.StringIO()

    # Write Lua module header
    tmp_config.write("-- Auto-generated configuration module\n")
    tmp_config.write("-- DO NOT EDIT - generated by pgosm-flex Python\n\n")
    tmp_config.write("local config = {\n")

    # Core configuration values
    tmp_config.write(f"    srid = {config.processing.srid},\n")
    tmp_config.write(f"    schema_name = '{config.processing.schema_name}',\n")
    tmp_config.write(f"    pgosm_date = '{config.region.pgosm_date}',\n")
    tmp_config.write(f"    pgosm_language = '{config.processing.language}',\n\n")

    # Load layerset configuration
    style_config = config.layerset.load_layerset_ini(flex_path)

    tmp_config.write("    layers = {\n")
    for layer, enabled in style_config.items():
        enabled_bool = enabled.lower() == "true"
        tmp_config.write(f"        {layer} = {str(enabled_bool).lower()},\n")
    tmp_config.write("    },\n\n")

    # Load index configurations for all enabled layers
    tmp_config.write("    indexes = {\n")
    for layer, enabled in style_config.items():
        if enabled.lower() == "true":
            tmp_config.write(f"        {layer} = ")
            _write_index_config(tmp_config, flex_path, layer)
            tmp_config.write(",\n")
    tmp_config.write("    },\n")

    tmp_config.write("}\n\n")
    tmp_config.write("return config\n")

    # Get the string contents and set as environment variable
    os.environ["PGOSM_LUA_CONFIG"] = tmp_config.getvalue()
    tmp_config.close()

    try:
        yield
    finally:
        # Unset environment variable after usage
        if "PGOSM_LUA_CONFIG" in os.environ:
            del os.environ["PGOSM_LUA_CONFIG"]


def run_replication_update(skip_nested, flex_path):
    """Runs osm2pgsql-replication between the DB start/finish steps.

    Parameters
    ----------
    skip_nested : bool
    flex_path : str

    Returns
    -------
    bool
        Indicates success/failure of replication process.
    """
    logger = logging.getLogger("pgosm-flex")
    conn_string = db.connection_string()

    # Generate Lua configuration module first
    with generate_lua_config() as lua_config_path, lua_style() as tmp_lua_style:
        update_cmd = f"""
    osm2pgsql-replication update -d $PGOSM_CONN \
        -- \
        --output=flex --style={tmp_lua_style.name} \
        --slim
        """

        update_cmd = update_cmd.replace("-d $PGOSM_CONN", f"-d {conn_string}")
        returncode = helpers.run_command_via_subprocess(
            cmd=update_cmd.split(), cwd=flex_path, print_to_log=True
        )

        if returncode != 0:
            err_msg = f"Failure. Return code: {returncode}"
            logger.warning(err_msg)
            return False

    db.osm2pgsql_replication_finish(skip_nested=skip_nested)
    logger.info("osm2pgsql-replication update complete")
    return True


def validate_region_inputs(region, subregion, input_file):
    """Ensures the combination of region, subregion and input_file is valid.

    No return, raises error when invalid.

    Parameters
    ----------
    region : str
    subregion : str
    input_file : str
    """
    if region is None and input_file is None:
        msg = "Either --region or --input-file must be provided"
        raise ValueError(msg)

    if region is None and subregion is not None:
        msg = "Cannot use --subregion without --region"
        raise ValueError(msg)

    if region is not None and "/" in region and subregion is None:
        err_msg = "Region provided appears to include subregion. "
        err_msg += 'The portion after the final "/" in the Geofabrik URL '
        err_msg += "should be the --subregion."
        raise ValueError(err_msg)


def setup_logger(debug):
    """Prepares logging.

    Parameters
    ----------
    debug : bool
        Enables debug mode when True.  INFO when False.
    """
    log_level = logging.DEBUG if debug else logging.INFO

    log_format = "%(asctime)s:%(levelname)s:%(name)s:%(module)s:%(message)s"
    logging.basicConfig(stream=sys.stdout, level=log_level, filemode="w", format=log_format)

    # Reduce verbosity of urllib3 logging
    logging.getLogger("urllib3").setLevel(logging.INFO)
    logger = logging.getLogger("pgosm-flex")
    logger.debug("Logger configured")


def get_paths():
    """Returns dictionary of various paths used.

    Ensures `out_path` exists.

    Returns
    -------
    paths : dict
    """
    from platformdirs import user_cache_dir

    config = get_config()
    base_path = Path(str(resources.files("pgosm_flex")))

    flex_path = base_path / "flex-config"
    db_path = base_path / "db"

    # Use data_dir from config, or platformdirs cache
    if config.processing.data_dir is not None:
        out_path = config.processing.data_dir
    else:
        cache_dir = user_cache_dir("pgosm-flex", "pgosm")
        out_path = Path(cache_dir)

    paths = {
        "base_path": base_path,
        "db_path": db_path,
        "out_path": out_path,
        "flex_path": flex_path,
    }

    out_path.mkdir(parents=True, exist_ok=True)

    return paths


def get_export_filename(input_file: str | None) -> str:
    """Returns the .sql filename to use for pg_dump."""
    # always set internally, even with --input-file and no --region
    config = get_config()
    region = config.region.region.replace("/", "-") if config.region.region else "unknown"
    subregion = config.region.subregion
    layerset = config.layerset.layerset
    pgosm_date = config.region.pgosm_date

    if subregion:
        subregion = subregion.replace("/", "-")

    if input_file:
        # Assumes .osm.pbf
        base_name = input_file[:-8]
        filename = f"{base_name}-{layerset}-{pgosm_date}.sql"
    elif subregion is None:
        filename = f"{region}-{layerset}-{pgosm_date}.sql"
    else:
        filename = f"{region}-{subregion}-{layerset}-{pgosm_date}.sql"

    return filename


def get_export_full_path(out_path, export_filename):
    """If `export_filename` is an absolute path, `out_path` is not considered.

    Parameters
    ----------
    out_path : str
    export_filename : str

    Returns
    -------
    export_path : str
    """
    if os.path.isabs(export_filename):
        export_path = export_filename
    else:
        export_path = os.path.join(out_path, export_filename)

    return export_path


def run_osm2pgsql(osm2pgsql_command, flex_path, debug):
    """Runs the provided osm2pgsql command.

    Parameters
    ----------
    osm2pgsql_command : str
    flex_path : str
    debug : boolean
    """
    logger = logging.getLogger("pgosm-flex")
    logger.info("Running osm2pgsql")

    returncode = helpers.run_command_via_subprocess(
        cmd=osm2pgsql_command.split(), cwd=flex_path, print_to_log=True
    )

    if returncode != 0:
        err_msg = f"Failed to run osm2pgsql. Return code: {returncode}"
        logger.error(err_msg)
        sys.exit(f"{err_msg} - Check the log output for details")

    logger.info("osm2pgsql completed")


def check_layerset_skip_nested_place(flex_path: str) -> bool:
    """If `place` layer is not included `skip_nested` should be true.

    Parameters
    ----------
    flex_path : str
        Path to the .ini file for the defined layerset defining which layers
        to include.

    Returns
    -------
    skip_nested : boolean
        Return True to disable nested place polygon (post-import processing)
    """
    logger = logging.getLogger("pgosm-flex")

    include_place = layerset_include_place(flex_path)

    logger.debug("--------------------------------------------")
    logger.debug(f"Place layer value: {type(include_place)}")
    logger.debug(f"Place layer value: {include_place}")
    logger.debug("--------------------------------------------")

    if include_place:
        logger.debug("Place layer is defined as true. Not setting skip_nested")
        return False

    logger.debug("Place layer not included")
    return True


def layerset_include_place(flex_path: str) -> bool:
    """
    Parameters
    ----------
    flex_path : str

    Returns
    -------
    place : bool
        If true, the Place layer will be included and post-processing functions
        should be called.
    """
    logger = logging.getLogger("pgosm-flex")
    config = get_config()

    layerset = config.layerset.layerset
    layerset_path = config.layerset.layerset_path

    if layerset_path is None:
        layerset_path_str = os.path.join(flex_path, "layerset")
        logger.info(f"Using default layerset path {layerset_path_str}")
    else:
        layerset_path_str = str(layerset_path)

    ini_file = os.path.join(layerset_path_str, f"{layerset}.ini")
    style_config = configparser.ConfigParser()
    style_config.read(ini_file)

    try:
        # Gets the value from INI
        # Comes through as str, convert to bool
        include_place = style_config["layerset"]["place"]
        logger.debug(f"Include place?  {include_place}")
        place = include_place.lower() == "true"
        logger.debug(f"Include place?  {place}")
    except KeyError:
        logger.debug("Place layer not defined, setting skip_nested")
        place = False

    return place


def run_post_processing(flex_path, skip_nested: bool) -> bool:
    """Runs steps following osm2pgsql import.

    Post-processing SQL scripts and (optionally) calculate nested admin polygons

    Parameters
    ----------
    flex_path : str
    skip_nested : bool

    Returns
    -------
    status : bool
    """
    from pathlib import Path

    logger = logging.getLogger("pgosm-flex")
    config = get_config()

    if not config.import_mode.run_post_sql:
        msg = "Running with --update append: Skipping post-processing SQL."
        msg += " Running osm2pgsql_replication_finish() instead."
        logger.info(msg)
        db.osm2pgsql_replication_finish(skip_nested=config.import_mode.skip_nested)
        return True

    # Load layerset configuration
    layerset_config = config.layerset.load_layerset_ini(Path(flex_path))

    # Run post-processing with config values
    post_processing_sql = db.pgosm_after_import(
        flex_path=flex_path,
        schema_name=config.processing.schema_name,
        skip_nested=skip_nested,
        layerset_config=layerset_config,
        conn_string=config.database.connection_string(),
    )

    if config.import_mode.skip_nested:
        logger.info("Skipping calculating nested polygons")
    else:
        logger.info("Calculating nested polygons")
        db.pgosm_nested_admin_polygons(flex_path, config.processing.schema_name)

    return post_processing_sql


def dump_database(input_file, out_path, pg_dump, skip_qgis_style):
    """Runs pg_dump when necessary to export the processed OpenStreetMap data.

    Parameters
    ----------
    input_file : str
    out_path : str
    pg_dump : bool
    skip_qgis_style : bool
    """
    if pg_dump:
        export_filename = get_export_filename(input_file)
        export_path = get_export_full_path(out_path, export_filename)

        db.run_pg_dump(export_path=export_path, skip_qgis_style=skip_qgis_style)
    else:
        logging.getLogger("pgosm-flex").info("Skipping pg_dump")


def check_replication_exists():
    """Checks if replication already setup, if so should only run update.

    Returns
    -------
    status : bool
    """
    logger = logging.getLogger("pgosm-flex")
    check_cmd = "osm2pgsql-replication status -d $PGOSM_CONN "
    logger.debug(f"Command to check DB for replication status:\n{check_cmd}")
    config = get_config()
    conn_string = config.database.connection_string()
    check_cmd = check_cmd.replace("-d $PGOSM_CONN", f"-d {conn_string}")

    returncode = helpers.run_command_via_subprocess(cmd=check_cmd.split(), cwd=None)

    if returncode != 0:
        logger.info("Replication not previously set up, fresh import.")
        logger.debug(f"Return code: {returncode}")
        return False

    logger.debug("Replication set up, candidate for update.")
    return True


def run_osm2pgsql_replication_init(pbf_path: str, pbf_filename: str) -> None:
    """Runs osm2pgsql-replication init to support replication mode.

    Parameters
    ----------
    pbf_path : str
    pbf_filename : str
    """
    logger = logging.getLogger("pgosm-flex")
    pbf_path = os.path.join(pbf_path, pbf_filename)
    init_cmd = "osm2pgsql-replication init -d $PGOSM_CONN "
    init_cmd += f"--osm-file {pbf_path}"
    logger.debug(f"Initializing DB for replication with command:\n{init_cmd}")
    config = get_config()
    conn_string = config.database.connection_string()
    init_cmd = init_cmd.replace("-d $PGOSM_CONN", f"-d {conn_string}")

    returncode = helpers.run_command_via_subprocess(
        cmd=init_cmd.split(), cwd=None, print_to_log=True
    )

    if returncode != 0:
        err_msg = f"Failed to run osm2pgsql-replication. Return code: {returncode}"
        logger.error(err_msg)
        sys.exit(f"{err_msg} - Check the log output for details.")

    logger.debug("osm2pgsql-replication init completed.")
