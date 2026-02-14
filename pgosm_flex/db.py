"""Module to interact with Postgres database.

Dynamic SQL is used in this module to allow customized schema names for storing
data. At a glance, this is vulnerable to SQLi (SQL Injection) considering the
``schema_name`` variable is technically "user input".  This is not considered
a concern for this project because the user inputting the ``schema_name`` value
is considered a trusted user.
"""

import logging
import os
import subprocess
import sys
import time

import psycopg
from psycopg import sql

from . import __version__, qgis_styles
from .config import get_config

LOGGER = logging.getLogger("pgosm-flex")


def wait_for_postgres():
    """Ensures Postgres service is reliably ready for use.

    Required b/c Postgres process in Docker gets restarted shortly
    after starting.  Calls `sys.exit()` after `max_loops` reached
    indicating failure due to inability to connect.
    """
    logger = logging.getLogger("pgosm-flex")
    logger.info("Checking for Postgres service to be available")
    log_pg_details()

    required_checks = 2
    found = 0
    i = 0
    max_loops = 30
    sleep_s = 3

    while found < required_checks:
        if i > max_loops:
            err = "Postgres still has not started. Exiting."
            logger.error(err)
            sys.exit()

        time.sleep(sleep_s)

        if pg_isready():
            found += 1
            logger.debug(f"Postgres up {found} times")

        if i % 5 == 0:
            logger.debug("Waiting for Postgres connection...")

        i += 1

    logger.info("Postgres instance ready")


def pg_isready() -> bool:
    """Checks for Postgres to be available.

    Uses pg_version_check() for simple approach.

    Returns
    -------
    pg_up : bool
    """
    try:
        result = pg_version_check()
    except AttributeError:
        err_msg = "Error checking version, likely waiting for Postgres to start."
        err_msg += " Only an error if it does not go away after a few attempts."
        logging.getLogger("pgosm-flex").warning(err_msg)
        return False

    if result is None:
        return False
    return True


def log_pg_details():
    """Logs non-sensitive Postgres connection details to LOGGER."""
    config = get_config()
    pg_host = config.database.host
    pg_port = config.database.port
    db_name = config.database.database
    pg_user = config.database.user

    msg = f'Connecting to Postgres using role "{pg_user}" on host '
    msg += f' "{pg_host}:{pg_port}"'
    msg += f'  in database "{db_name}"'
    LOGGER.info(msg)


def prepare_pgosm_db(db_path):
    """Runs through steps to prepare the target database for PgOSM Flex.

    Includes additional preparation for using --replication and --updated=append
    modes.

    Parameters
    ----------
    db_path : str
    """
    config = get_config()

    drop_it = True

    LOGGER.debug(
        "Running standard database prep for localhost database. Includes DROP/CREATE DATABASE"
    )
    LOGGER.debug(f"import_mode: {config.import_mode.as_json()}")

    if config.import_mode.slim_no_drop:
        if not config.import_mode.append_first_run:
            drop_it = False
        if config.import_mode.replication_update:
            drop_it = False

    if drop_it:
        LOGGER.debug("Dropping local database if exists")
        drop_pgosm_schema_tables()
    else:
        LOGGER.debug(
            "Not dropping local DB. This is expected with subsequent import via --replication OR --update=append."
        )

    create_pgosm_db()

    prepare_osm_schema(db_path=db_path)
    run_insert_pgosm_road(db_path=db_path, schema_name=config.processing.schema_name)

    if config.import_mode.replication_update or config.import_mode.update == "append":
        osm2pgsql_replication_start()


def start_import(osm2pgsql_version, schema_name):
    """Creates record in osm.pgosm_flex table.

    Parameters
    ----------
    osm2pgsql_version : str

    Returns
    -------
    import_id : int
        Value from the `id` column in `osm.pgosm_flex`.
    """
    config = get_config()
    params = {
        "pgosm_region": config.region.region,
        "pgosm_date": config.region.pgosm_date,
        "srid": config.processing.srid,
        "language": config.processing.language,
        "layerset": config.layerset.layerset,
        "git_info": __version__,
        "osm2pgsql_version": osm2pgsql_version,
        "import_mode": config.import_mode.as_json(),
        "input_file": str(config.region.input_file),
    }

    sql_raw = """
        INSERT INTO {schema_name}.pgosm_flex
            (osm_date, region, pgosm_flex_version, srid,
                osm2pgsql_version, "language", import_mode,
                layerset, input_file)
            VALUES(%(pgosm_date)s, %(pgosm_region)s, %(git_info)s, %(srid)s,
                %(osm2pgsql_version)s,
                COALESCE(%(language)s, ''), %(import_mode)s, %(layerset)s,
                %(input_file)s
                )
            RETURNING id
        ;
    """
    sql_raw = sql_raw.format(schema_name=config.processing.schema_name)
    with get_db_conn(conn_string=config.database.connection_string()) as conn:
        cur = conn.cursor()
        cur.execute(sql_raw, params=params)
        import_id = cur.fetchone()[0]

    return import_id


def pg_version_check():
    """Checks Postgres machine-readable server_version_num.

    Sends to logs and returns value.

    Results
    --------------------
    pg_version : int
    """
    sql_raw = """
        SELECT setting
            FROM pg_catalog.pg_settings
            WHERE name = 'server_version_num'
    """
    config = get_config()

    with get_db_conn(conn_string=config.database.connection_string()) as conn:
        cur = conn.cursor()
        cur.execute(sql_raw)
        results = cur.fetchone()

    # It's an int https://www.postgresql.org/docs/current/runtime-config-preset.html#GUC-SERVER-VERSION-NUM
    pg_version = int(results[0])
    if pg_version < 120000:
        err_msg = f"Postgres version {pg_version} not supported. Postgres 12+ required."
        LOGGER.error(err_msg)
        sys.exit(9)

    return pg_version


def drop_pgosm_schema_tables() -> None:
    """Drops the pgosm database schema tables if they exist."""
    config = get_config()

    sql_stmt = sql.SQL("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = {}
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """).format(config.processing.schema_name)

    LOGGER.debug("Setting Pg conn to enable autocommit - required for drop/create DB")

    with get_db_conn(conn_string=config.database.connection_string()) as conn:
        cursor = conn.cursor()
        cursor.execute(sql_stmt)
        results = cursor.fetchall()

        if len(results) > 0:
            if config.import_mode.force:
                LOGGER.info("Force drop all tables")
                for table in results:
                    sql_drop_table = sql.SQL("DROP TABLE IF EXISTS {}.{} CASCADE").format(
                        sql.Identifier(config.processing.schema_name), sql.Identifier(table[0])
                    )
                    cursor.execute(sql_drop_table)
                conn.close()
                LOGGER.info(f"Dropped tables in schema {config.processing.schema_name}")
            else:
                LOGGER.error("Schema not empty; use --force to remove existing tables")
                sys.exit(1)


def create_pgosm_db():
    """Creates the pgosm database and prepares with PostGIS and osm schema

    Returns
    -------
    status : bool
    """
    config = get_config()

    sql_stmt = sql.SQL("CREATE DATABASE {}").format(sql.Identifier(config.database.database))

    conn = get_db_conn(conn_string=config.database.connection_string())

    LOGGER.debug("Setting Pg conn to enable autocommit - required for drop/create DB")
    conn.autocommit = True

    try:
        conn.execute(sql_stmt)
        LOGGER.info("Created pgosm database")
    except psycopg.errors.DuplicateDatabase:
        LOGGER.info("Database already existed.")
    finally:
        conn.close()


def prepare_osm_schema(db_path: str):
    """Runs deploy scripts to prepare the PgOSM Flex database.

    This function's code could be simplified, but currently I like the verbosity
    of it. It doesn't need to stay like this forever, but for now... it's fine.

    Parameters
    ----------
    db_path : str
        Path to folder with SQL scripts.
    skip_qgis_style : bool
    scheme_name : str
    """
    config = get_config()

    LOGGER.info(f"Preparing database schema: {config.processing.schema_name}")
    create_osm_file = "osm.sql"
    create_osm_pgosm_flex_file = "osm_pgosm_flex.sql"
    create_pgosm_road_file = "pgosm_road.sql"
    create_replication_functions = "replication_functions.sql"
    create_routing_functions = "routing_functions.sql"

    run_deploy_file(
        db_path=db_path, sql_filename=create_osm_file, schema_name=config.processing.schema_name
    )
    run_deploy_file(
        db_path=db_path,
        sql_filename=create_osm_pgosm_flex_file,
        schema_name=config.processing.schema_name,
    )
    run_deploy_file(
        db_path=db_path,
        sql_filename=create_pgosm_road_file,
        schema_name=config.processing.schema_name,
    )
    run_deploy_file(
        db_path=db_path,
        sql_filename=create_replication_functions,
        schema_name=config.processing.schema_name,
    )
    run_deploy_file(
        db_path=db_path,
        sql_filename=create_routing_functions,
        schema_name=config.processing.schema_name,
    )

    if config.import_mode.skip_qgis_style:
        LOGGER.info("Skipping QGIS styles")
    else:
        LOGGER.info("Loading QGIS styles")
        qgis_styles.load_qgis_styles(db_path=db_path, db_name=config.database.database)


def run_insert_pgosm_road(db_path: str, schema_name: str):
    """Runs script to load data to pgosm.road table.

    Parameters
    ----------
    db_path : str
    schema_name : str
        Schema name for OpenStreetMap data
    """
    sql_filename = "roads-us.sql"
    run_deploy_file(
        db_path=db_path, sql_filename=sql_filename, schema_name=schema_name, subfolder="data"
    )


def run_deploy_file(db_path: str, sql_filename: str, schema_name: str, subfolder: str = "deploy"):
    """Run a SQL script under the deploy path.  Used to setup PgOSM Flex DB.

    Parameters
    ----------
    db_path : str
        Path to folder with SQL scripts.
    sql_filename : sql_filename
    subfolder : str
        Set subfolder under db_path.
        Default: deploy
    schema_name : str
        Schema name for OpenStreetMap data
    """
    config = get_config()
    full_path = os.path.join(db_path, subfolder, sql_filename)
    LOGGER.info(f"Deploying {full_path}")

    with open(full_path) as f:
        deploy_sql = f.read()

    deploy_sql = deploy_sql.format(schema_name=schema_name)

    with get_db_conn(conn_string=config.database.connection_string()) as conn:
        cur = conn.cursor()
        cur.execute(deploy_sql)
        LOGGER.debug(f"Ran SQL in {sql_filename}")


def get_db_conn(conn_string):
    """Establishes psycopg database connection.

    Parameters
    ----------
    conn_string : str

    Returns
    -------
    conn : psycopg.Connection
    """
    try:
        conn = psycopg.connect(conn_string)
        LOGGER.debug("Connection to Postgres established")
    except psycopg.OperationalError as err:
        err_msg = f"Database connection error. Error: {err}"
        LOGGER.error(err_msg)
        raise err

    return conn


def run_post_processing_sql(
    flex_path: str, layer_name: str, schema_name: str, conn_string: str
) -> bool:
    """Executes post-processing SQL file for a specific layer.

    Parameters
    ----------
    flex_path : str
        Path to flex-config directory
    layer_name : str
        Name of the layer (maps to SQL filename)
    schema_name : str
        Target schema name for substitution
    conn_string : str
        Database connection string

    Returns
    -------
    bool
        True if SQL executed successfully, False on error
    """
    sql_file_path = os.path.join(flex_path, "sql", f"{layer_name}.sql")

    try:
        LOGGER.info(f"Processing layer: {layer_name}")

        with open(sql_file_path) as f:
            sql_content = f.read()

        # Schema name substitution - use replace() not format()
        # SQL files may contain { } characters
        sql_content = sql_content.replace("osm.", f"{schema_name}.")

        with get_db_conn(conn_string=conn_string) as conn:
            cur = conn.cursor()
            cur.execute(sql_content)

        LOGGER.debug(f"Successfully processed {layer_name}")
        return True

    except FileNotFoundError:
        LOGGER.error(f"SQL file not found: {sql_file_path}")
        return False
    except psycopg.Error as e:
        LOGGER.error(f"Database error processing {layer_name}: {e}")
        return False
    except Exception as e:
        LOGGER.error(f"Error processing {layer_name}: {e}")
        return False


def pgosm_after_import(
    flex_path: str, schema_name: str, skip_nested: bool, layerset_config: dict, conn_string: str
) -> bool:
    """Runs post-processing SQL for enabled layers.

    Replaces previous Lua-based implementation (run-sql.lua) with native Python.
    Executes SQL files for each enabled layer based on layerset configuration.

    Parameters
    ----------
    flex_path : str
        Path to flex-config directory containing SQL files
    schema_name : str
        Target schema name for OpenStreetMap data
    skip_nested : bool
        If True, skip processing place_polygon_nested
    layerset_config : dict
        Dictionary of layer names to enabled status from INI file
    conn_string : str
        Database connection string

    Returns
    -------
    bool
        True if all SQL executed successfully, False if any errors occurred
    """
    LOGGER.info("Running post-processing...")
    LOGGER.debug(f"Schema name: {schema_name}")
    LOGGER.debug(f"Skip nested: {skip_nested}")
    LOGGER.debug(f"Loaded layerset config with {len(layerset_config)} layers")

    # Define layers to process (matches Lua's layer list)
    # Must match order and naming from run-sql.lua:39-43
    layers = [
        "amenity",
        "building",
        "building_combined_point",
        "indoor",
        "infrastructure",
        "landuse",
        "leisure",
        "natural",
        "place",
        "poi",
        "public_transport",
        "road",
        "road_major",
        "shop",
        "shop_combined_point",
        "tags",
        "traffic",
        "unitable",
        "water",
    ]

    error_count = 0

    # Handle place_polygon_nested (runs when NOT skip_nested)
    # Note: Lua code had logic bug (checked truthy string), we fix it here
    if not skip_nested:
        LOGGER.info("Processing place_polygon_nested")
        if not run_post_processing_sql(flex_path, "place_polygon_nested", schema_name, conn_string):
            error_count += 1
    else:
        LOGGER.info("Skipping place_polygon_nested (skip_nested=True)")

    # Process each enabled layer
    for layer in layers:
        # Check if layer is enabled in layerset config
        # INI values come as strings 'true' or 'false'
        if layer in layerset_config and layerset_config[layer].lower() == "true":
            if not run_post_processing_sql(flex_path, layer, schema_name, conn_string):
                error_count += 1
        else:
            LOGGER.debug(f"Skipping layer: {layer} (not enabled in layerset)")

    if error_count > 0:
        LOGGER.error(f"Post-processing completed with {error_count} error(s)")
        return False

    LOGGER.info("Post-processing completed successfully")
    return True


def pgosm_nested_admin_polygons(flex_path: str, schema_name: str):
    """Runs two stored procedures to calculate nested admin polygons via psql.

    Parameters
    ----------
    flex_path : str
    schema_name : str
    """
    config = get_config()

    # Populate the table
    sql_raw_1 = f"CALL {schema_name}.populate_place_polygon_nested();"

    conn_string = config.database.connection_string()
    cmds = ["psql", "-d", conn_string, "-c", sql_raw_1]
    LOGGER.info("Populating place_polygon_nested table (osm.populate_place_polygon_nested() )")
    output = subprocess.run(
        cmds,
        text=True,
        cwd=flex_path,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    LOGGER.info(f"Nested polygon output: \n {output.stdout}")

    if output.returncode != 0:
        err_msg = f"Failed to populate nested polygon data. Return code: {output.returncode}"
        LOGGER.error(err_msg)
        sys.exit(f"{err_msg} - Check the log output for details.")

    # Build the data
    sql_raw_2 = f" CALL {schema_name}.build_nested_admin_polygons();"

    cmds = ["psql", "-d", conn_string, "-c", sql_raw_2]
    LOGGER.info("Building nested polygons... (this can take a while)")
    output = subprocess.run(
        cmds,
        text=True,
        cwd=flex_path,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    LOGGER.info(f"Nested polygon output: \n {output.stdout}")

    if output.returncode != 0:
        err_msg = f"Failed to build nested polygons. Return code: {output.returncode}"
        LOGGER.error(err_msg)
        sys.exit(f"{err_msg} - Check the log output for details.")


def osm2pgsql_replication_start():
    """Runs pre-replication step to clean out FKs that would prevent updates.

    This function is necessary for using `--replication (osm2pgsql-replication)
    and `--update append` mode.
    """
    config = get_config()
    LOGGER.info("Prep database to allow data updates.")
    sql_raw = "CALL osm.append_data_start();"

    with get_db_conn(conn_string=config.database.connection_string()) as conn:
        cur = conn.cursor()
        cur.execute(sql_raw)


def osm2pgsql_replication_finish(skip_nested: bool):
    """Runs post-replication step to refresh materialized views and rebuild
    nested data when appropriate.

    Only needed for `--replication`, not used for `--update append` mode.

    Parameters
    ----------
    skip_nested : bool
    """
    config = get_config()

    # Fails via psycopg, using psql
    if skip_nested:
        LOGGER.info("Finishing Replication, skipping nested polygons")
        sql_raw = "CALL osm.append_data_finish(skip_nested := True );"
    else:
        LOGGER.info("Finishing Replication, including nested polygons")
        sql_raw = "CALL osm.append_data_finish(skip_nested := False );"

    conn_string = config.database.connection_string()
    cmds = ["psql", "-d", conn_string, "-c", sql_raw]
    LOGGER.info("Finishing Replication")
    output = subprocess.run(
        cmds, text=True, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    LOGGER.info(f"Finishing replication output: \n {output.stdout}")

    if output.returncode != 0:
        err_msg = f"Failed to finish replication. Return code: {output.returncode}"
        LOGGER.error(err_msg)
        sys.exit(f"{err_msg} - Check the log output for details.")


def run_pg_dump(export_path, skip_qgis_style):
    """Runs pg_dump to save processed data to load into other PostGIS DBs.

    Parameters
    ----------
    export_path : str
        Absolute path to output .sql file
    skip_qgis_style : bool
    """
    config = get_config()
    logger = logging.getLogger("pgosm-flex")
    conn_string = config.database.connection_string()
    schema_name = "osm"

    if skip_qgis_style:
        logger.info(f"Running pg_dump (only {schema_name} schema)")
        cmds = ["pg_dump", "-d", conn_string, f"--schema={schema_name}", "-f", export_path]
    else:
        logger.info(f"Running pg_dump ({schema_name} schema plus extras)")
        cmds = [
            "pg_dump",
            "-d",
            conn_string,
            f"--schema={schema_name}",
            "--schema=pgosm",
            "--schema=public",
            "-f",
            export_path,
        ]

    output = subprocess.run(cmds, text=True, capture_output=True, check=False)
    LOGGER.info(f"pg_dump complete, saved to {export_path}")
    LOGGER.debug(f"pg_dump output: \n {output.stderr}")
    fix_pg_dump_create_public(export_path)


def fix_pg_dump_create_public(export_path: str):
    """Using pg_dump with `--schema=public` results in
    a .sql script containing `CREATE SCHEMA public;`, nearly always breaks
    in target DB.  Replaces with `CREATE SCHEMA IF NOT EXISTS public;`

    Parameters
    ----------
    export_path : str
    """
    # Read the file content
    with open(export_path) as f:
        content = f.read()

    # Replace the problematic CREATE SCHEMA statement
    content = content.replace("CREATE SCHEMA public;", "CREATE SCHEMA IF NOT EXISTS public;")

    # Write back to the same file
    with open(export_path, "w") as f:
        f.write(content)

    LOGGER.debug("Completed replacement to not fail when public schema exists")


def log_import_message(import_id: int, msg: str, schema_name: str):
    """Logs msg to database in osm.pgosm_flex for import_uuid.

    Overwrites `osm_date` if `pbf_timestamp` is set.

    Parameters
    ----------
    import_id : int
    msg : str
    schema_name: str
    """
    config = get_config()

    sql_raw = """
UPDATE {schema_name}.pgosm_flex
    SET import_status = %(msg)s ,
        osm_date = COALESCE( %(pbf_timestamp)s , osm_date)
    WHERE id = %(import_id)s
;
"""
    sql_raw = sql_raw.format(schema_name=schema_name)
    with get_db_conn(conn_string=config.database.connection_string()) as conn:
        params = {"import_id": import_id, "msg": msg, "pbf_timestamp": config.region.pgosm_date}
        cur = conn.cursor()
        cur.execute(sql_raw, params=params)


def get_prior_import(schema_name: str) -> dict:
    """Gets the latest import details from osm.pgosm_flex.

    Parameters
    ----------
    schema_name : str

    Returns
    -------
    results : dict
    """
    config = get_config()
    sql_raw = """
        SELECT id, osm_date, region, layerset, import_status,
                import_mode ->> 'replication' AS replication,
                import_mode ->> 'update' AS use_update,
                import_mode,
                split_part(pgosm_flex_version, '-', 1) AS pgosm_flex_version_no_hash
            FROM {schema_name}.pgosm_flex
            ORDER BY imported DESC
            LIMIT 1
    """
    sql_raw = sql_raw.format(schema_name=schema_name)
    with get_db_conn(conn_string=config.database.connection_string()) as conn:
        cur = conn.cursor(row_factory=psycopg.rows.dict_row)
        results = cur.execute(sql_raw).fetchone()

    if results is None:
        results = {}

    return results
