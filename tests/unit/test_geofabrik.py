"""Unit tests to cover the Geofabrik module."""

import pytest
import unittest

from pgosm_flex import geofabrik, helpers, config

REGION_US = "north-america/us"
SUBREGION_DC = "district-of-columbia"
LAYERSET = "default"
PGOSM_DATE = "2021-01-13"

PBF_FILE_WITH_DATE = f"/app/tests/data/district-of-columbia-{PGOSM_DATE}.osm.pbf"
MD5_FILE_WITH_DATE = f"/app/tests/data/district-of-columbia-{PGOSM_DATE}.osm.pbf.md5"


@pytest.fixture
def default_config():
    yield config.config_context(config.init_config({
        "region": REGION_US,
        "subregion": SUBREGION_DC,
        "srid": "3857",
        "language": None,
        "pgosm_date": PGOSM_DATE,
        "layerset": LAYERSET,
        "layerset_path": None,
        "schema_name": "osm",
        "skip_nested": True,
        "ram": 8
    }))


def test_get_region_filename_returns_subregion_when_exists(default_config):
    with default_config:
        result = geofabrik.get_region_filename()
        expected = f"{SUBREGION_DC}-latest.osm.pbf"
        assert expected == result


def test_get_region_filename_returns_region_when_subregion_None(default_config):
    """Override Subregion to None"""
    with default_config as cfg:
        cfg.region.subregion = None
        result = geofabrik.get_region_filename()
        expected = f"{REGION_US}-latest.osm.pbf"
        assert expected == result


def test_get_pbf_url_returns_with_region_and_subregion(default_config):
    with default_config:
        region = REGION_US
        subregion = SUBREGION_DC
        result = geofabrik.get_pbf_url(region, subregion)
        expected = f"https://download.geofabrik.de/{region}/{subregion}-latest.osm.pbf"
        assert expected == result


def test_get_pbf_url_returns_with_region_and_subregion_as_none(default_config):
    with default_config:
        region = REGION_US
        subregion = None
        result = geofabrik.get_pbf_url(region, subregion)
        expected = f"https://download.geofabrik.de/{region}-latest.osm.pbf"
        assert expected == result


def test_pbf_download_needed_returns_boolean(default_config):
    with default_config:
        pgosm_date = geofabrik.helpers.get_today()
        expected = bool
        result = geofabrik.pbf_download_needed(
            pbf_file_with_date="does-not-matter",
            md5_file_with_date="not-a-file",
            pgosm_date=pgosm_date,
        )
        assert expected is type(result)


def test_pbf_download_needed_returns_true_when_file_not_exists(default_config):
    with default_config:
        pgosm_date = geofabrik.helpers.get_today()
        expected = True
        result = geofabrik.pbf_download_needed(
            pbf_file_with_date="does-not-matter",
            md5_file_with_date="not-a-file",
            pgosm_date=pgosm_date,
        )
        assert expected == result
