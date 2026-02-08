"""Generic functions and attributes used in multiple modules of PgOSM Flex."""

import datetime
import logging
import os
import subprocess
import sys
from time import sleep

DEFAULT_SRID = "3857"


def get_today() -> str:
    """Returns yyyy-mm-dd formatted string for today.

    Returns
    -------
    today : str
    """
    today = datetime.datetime.today().strftime("%Y-%m-%d")
    return today


def run_command_via_subprocess(
    cmd: list, cwd: str | None, output_lines: list | None = None, print_to_log: bool = False
) -> int:
    """Wraps around subprocess.Popen() to run commands outside of Python. Prints
    output as it goes, returns the status code from the command.

    Parameters
    ----------
    cmd : list
        Parts of the command to run.
    cwd : str or None
        Set the working directory, or to None.
    output_lines : list
        Pass in a list to return the output details.
    print_to_log : bool
        Default False.  Set to true to also print to logger

    Returns
    -------
    status : int
        Return code from command
    """
    output_lines = output_lines or []
    logger = logging.getLogger("pgosm-flex")
    with subprocess.Popen(
        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    ) as process:
        while True:
            assert process.stdout is not None  # We create Popen with stdout=PIPE
            output = process.stdout.readline()
            if process.poll() is not None and output == b"":
                break

            if output:
                ln = output.strip().decode("utf-8")
                output_lines.append(ln)
                if print_to_log:
                    logger.info(ln)
            else:
                # Only sleep when there wasn't output
                sleep(1)

        status = process.poll()
        assert status is not None  # Process has finished
    return status


def verify_checksum(md5_file: str, path: str):
    """Verifies checksum of osm pbf file.

    If verification fails calls `sys.exit()`

    Parameters
    ----------
    md5_file : str
        Filename of the MD5 file to verify the osm.pbf file.
    path : str
        Path to directory with `md5_file` to validate
    """
    logger = logging.getLogger("pgosm-flex")
    logger.debug(f"Validating {md5_file} in {path}")

    import hashlib

    md5 = hashlib.md5()

    with open(md5_file.replace(".md5", ""), "rb") as f:
        while chunk := f.read(8192):
            md5.update(chunk)
        actual_md5 = md5.hexdigest()

    with open(md5_file) as f:
        expected_md5 = f.read().strip().split()[0]

    if actual_md5 != expected_md5:
        err_msg = f"Failed to validate md5sum. Expected: {expected_md5}, Actual: {actual_md5}"
        logger.error(err_msg)
        sys.exit(err_msg)

    logger.debug("md5sum validated")


def get_region_combined(region: str, subregion: str | None) -> str:
    """Returns combined region with optional subregion.

    Parameters
    ----------
    region : str
    subregion : str (or None)

    Returns
    -------
    pgosm_region : str
    """
    if subregion is None:
        pgosm_region = region
    else:
        os.environ["PGOSM_SUBREGION"] = subregion
        pgosm_region = f"{region}-{subregion}"

    return pgosm_region
