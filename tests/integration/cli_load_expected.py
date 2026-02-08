#: Tables expected to be created with layerset = "default"
LAYERSET_DEFAULT_TABLES = [
    "amenity_line",
    "amenity_point",
    "amenity_polygon",
    "building_point",
    "building_polygon",
    "indoor_line",
    "indoor_point",
    "indoor_polygon",
    "infrastructure_line",
    "infrastructure_point",
    "infrastructure_polygon",
    "landuse_point",
    "landuse_polygon",
    "leisure_point",
    "leisure_polygon",
    "natural_line",
    "natural_point",
    "natural_polygon",
    "pgosm_flex",
    "place_line",
    "place_point",
    "place_polygon",
    # "place_polygon_nested",  # Only created when --skip-nested is False
    "poi_line",
    "poi_point",
    "poi_polygon",
    "public_transport_line",
    "public_transport_point",
    "public_transport_polygon",
    "road_line",
    "road_point",
    "road_polygon",
    "shop_point",
    "shop_polygon",
    "tags",
    "traffic_line",
    "traffic_point",
    "traffic_polygon",
    "water_line",
    "water_point",
    "water_polygon",
]

#: Tables expected to be created with layerset = "basic"
LAYERSET_BASIC_TABLES = [
    "building_combined_point",
    "landuse_point",
    "landuse_polygon",
    "pgosm_flex",
    "place_line",
    "place_point",
    "place_polygon",
    "poi_combined_point",
    "road_major",
    "unitable",
]

#: Tables expected to be created with layerset = "minimal"
LAYERSET_MINIMAL_TABLES = [
    "pgosm_flex",
    "place_line",
    "place_point",
    "place_polygon",
    "poi_combined_point",
    "road_major",
]

LAYERSET_EVERYTHING_TABLES = LAYERSET_DEFAULT_TABLES + [
    "building_combined_point",
    "poi_combined_point",
    "shop_combined_point",
    "unitable",
]
