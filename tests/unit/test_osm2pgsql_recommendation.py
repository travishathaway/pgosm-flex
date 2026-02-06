"""Unit tests to cover the osm2pgsql_recommendation module."""

from pgosm_flex import osm2pgsql_recommendation
from pgosm_flex.config import ImportConfig


def test_get_recommended_script_returns_type_str():
    expected = str
    system_ram_gb = 2
    osm_pbf_gb = 10
    im = ImportConfig(
        replication=False, replication_update=False, update=None, force=False
    )
    pbf_filename = "This-is-a-test.osm.pbf"
    output_path = "this-is-a-test"
    result = osm2pgsql_recommendation.get_recommended_script(
        system_ram_gb=system_ram_gb,
        osm_pbf_gb=osm_pbf_gb,
        import_mode=im,
        pbf_filename=pbf_filename,
        output_path=output_path,
    )

    actual = type(result)
    assert expected == actual


def test_get_recommended_script_returns_expected_value_simple_example():
    expected = "osm2pgsql -d postgresql://postgres@localhost:5432/pgosm?application_name=pgosm-flex  --cache=0  --slim  --drop  --flat-nodes=/tmp/nodes  --create  --output=flex --style=./run.lua  This-is-a-test.osm.pbf"
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
    )
    assert expected == actual


def test_get_recommended_script_returns_expected_value_update_create():
    expected = "osm2pgsql -d postgresql://postgres@localhost:5432/pgosm?application_name=pgosm-flex  --cache=0  --slim  --flat-nodes=/tmp/nodes  --create  --output=flex --style=./run.lua  This-is-a-test.osm.pbf"
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
    )
    assert expected == actual


def test_get_recommended_script_returns_expected_value_update_append():
    expected = "osm2pgsql -d postgresql://postgres@localhost:5432/pgosm?application_name=pgosm-flex  --cache=0  --slim  --flat-nodes=/tmp/nodes  --append  --output=flex --style=./run.lua  This-is-a-test.osm.pbf"
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
    )
    assert expected == actual


def test_get_recommended_script_returns_expected_value_replication_first():
    """NOTE:  This function does not have a counterpart testing when
    replication_update = True.  This is intentional,
    osm2pgsql-tuner is not involved at those steps so no recommended script
    is generated.
    """
    expected = "osm2pgsql -d postgresql://postgres@localhost:5432/pgosm?application_name=pgosm-flex  --cache=0  --slim  --flat-nodes=/tmp/nodes  --create  --output=flex --style=./run.lua  This-is-a-test.osm.pbf"
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
    )
    assert expected == actual
