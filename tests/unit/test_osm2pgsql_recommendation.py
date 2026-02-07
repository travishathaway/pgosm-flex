"""Unit tests to cover the osm2pgsql_recommendation module."""

import pytest
from pgosm_flex import osm2pgsql_recommendation, config
from pgosm_flex.config import ImportConfig


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


def test_get_recommended_script_returns_type_str(default_config):
    with default_config:
        expected = str
        system_ram_gb = 2
        osm_pbf_gb = 10
        im = ImportConfig(
            replication=False, replication_update=False, update=None, force=False
        )
        pbf_filename = "This-is-a-test.osm.pbf"
        output_path = "this-is-a-test"
        pgosm_layer_set = "/tmp/test_style.lua"
        result = osm2pgsql_recommendation.get_recommended_script(
            system_ram_gb=system_ram_gb,
            osm_pbf_gb=osm_pbf_gb,
            import_mode=im,
            pbf_filename=pbf_filename,
            output_path=output_path,
            pgosm_layer_set=pgosm_layer_set,
        )

        actual = type(result)
        assert expected == actual


def test_get_recommended_script_returns_expected_value_simple_example(default_config):
    with default_config:
        pgosm_layer_set = "/tmp/test_style.lua"
        expected = f"osm2pgsql -d postgresql://postgres@localhost:5432/pgosm?application_name=pgosm-flex  --cache=0  --slim  --drop  --flat-nodes=/tmp/nodes  --create  --output=flex --style={pgosm_layer_set} This-is-a-test.osm.pbf"
        system_ram_gb = 2
        osm_pbf_gb = 10
        im = ImportConfig(
            replication=False, replication_update=False, update=None, force=False
        )
        pbf_filename = "This-is-a-test.osm.pbf"
        output_path = "this-is-a-test"
        actual = osm2pgsql_recommendation.get_recommended_script(
            system_ram_gb=system_ram_gb,
            osm_pbf_gb=osm_pbf_gb,
            import_mode=im,
            pbf_filename=pbf_filename,
            output_path=output_path,
            pgosm_layer_set=pgosm_layer_set,
        )
        assert expected == actual


def test_get_recommended_script_returns_expected_value_update_create(default_config):
    with default_config:
        pgosm_layer_set = "/tmp/test_style.lua"
        expected = f"osm2pgsql -d postgresql://postgres@localhost:5432/pgosm?application_name=pgosm-flex  --cache=0  --slim  --flat-nodes=/tmp/nodes  --create  --output=flex --style={pgosm_layer_set} This-is-a-test.osm.pbf"
        system_ram_gb = 2
        osm_pbf_gb = 10
        im = ImportConfig(
            replication=False, replication_update=False, update="create", force=False
        )
        pbf_filename = "This-is-a-test.osm.pbf"
        output_path = "this-is-a-test"
        actual = osm2pgsql_recommendation.get_recommended_script(
            system_ram_gb=system_ram_gb,
            osm_pbf_gb=osm_pbf_gb,
            import_mode=im,
            pbf_filename=pbf_filename,
            output_path=output_path,
            pgosm_layer_set=pgosm_layer_set,
        )
        assert expected == actual


def test_get_recommended_script_returns_expected_value_update_append(default_config):
    with default_config:
        pgosm_layer_set = "/tmp/test_style.lua"
        expected = f"osm2pgsql -d postgresql://postgres@localhost:5432/pgosm?application_name=pgosm-flex  --cache=0  --slim  --flat-nodes=/tmp/nodes  --append  --output=flex --style={pgosm_layer_set} This-is-a-test.osm.pbf"
        system_ram_gb = 2
        osm_pbf_gb = 10
        im = ImportConfig(
            replication=False, replication_update=False, update="append", force=False
        )
        pbf_filename = "This-is-a-test.osm.pbf"
        output_path = "this-is-a-test"
        actual = osm2pgsql_recommendation.get_recommended_script(
            system_ram_gb=system_ram_gb,
            osm_pbf_gb=osm_pbf_gb,
            import_mode=im,
            pbf_filename=pbf_filename,
            output_path=output_path,
            pgosm_layer_set=pgosm_layer_set,
        )
        assert expected == actual


def test_get_recommended_script_returns_expected_value_replication_first(default_config):
    """NOTE:  This function does not have a counterpart testing when
    replication_update = True.  This is intentional,
    osm2pgsql-tuner is not involved at those steps so no recommended script
    is generated.
    """
    with default_config:
        pgosm_layer_set = "/tmp/test_style.lua"
        expected = f"osm2pgsql -d postgresql://postgres@localhost:5432/pgosm?application_name=pgosm-flex  --cache=0  --slim  --flat-nodes=/tmp/nodes  --create  --output=flex --style={pgosm_layer_set} This-is-a-test.osm.pbf"
        system_ram_gb = 2
        osm_pbf_gb = 10
        im = ImportConfig(
            replication=True, replication_update=False, update=None, force=False
        )
        pbf_filename = "This-is-a-test.osm.pbf"
        output_path = "this-is-a-test"
        actual = osm2pgsql_recommendation.get_recommended_script(
            system_ram_gb=system_ram_gb,
            osm_pbf_gb=osm_pbf_gb,
            import_mode=im,
            pbf_filename=pbf_filename,
            output_path=output_path,
            pgosm_layer_set=pgosm_layer_set,
        )
        assert expected == actual
