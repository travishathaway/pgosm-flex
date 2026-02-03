"""Unit tests to cover the DB module."""

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
