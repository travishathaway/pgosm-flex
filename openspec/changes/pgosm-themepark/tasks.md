# Tasks: pgosm-themepark

## Phase 1: Scaffold

- [x] Create `pgosm-themepark/` directory at the repo root with subdirectories:
  `themes/pgosm/topics/`, `config/`

- [ ] Verify the installed `osm2pgsql-themepark` package on gis-forge to confirm:
  - The Lua framework path under `$CONDA_PREFIX` (needed for activation scripts)
  - That `core/name-with-fallback` is available

## Phase 2: Theme Init

- [x] Create `themes/pgosm/init.lua`
  - Port all shared helper functions from `helpers.lua`: `parse_to_meters`, `parse_speed`,
    `parse_layer_value`, `major_road`, `starts_with`, `ends_with`, `get_ref`,
    `parse_admin_level`, `get_address`, `get_wheelchair_desc`, `routable_foot`,
    `routable_cycle`, `routable_motor`
  - Port building helpers from `style/building_helpers.lua`:
    `is_first_level_building`, `address_only_building`, `get_osm_type_subtype_building`
  - Port POI helpers from `style/poi_helpers.lua`
  - Port shop helpers from `style/shop_helpers.lua`
  - Expose all functions on the returned `theme` table
  - Remove: `get_name`, `get_name_last_ditch`, `get_indexes_from_spec`, and all
    index-related helpers (these are replaced by Themepark)
  - Remove: config loading via `PGOSM_LUA_CONFIG` env var (no longer needed)

## Phase 3: Port Topics (20 topics)

For each topic, the mechanical transformation is:
- `osm2pgsql.define_table(...)` → `themepark:add_table({ ..., indexes = { { column='geom', method='gist' }, { column='osm_type', method='btree' } } })`
- Tables with a name column: wrap columns in `themepark:columns('core/name', { ... })`
- `function topic_process_node(object)` + chaining boilerplate → `themepark:add_proc('node', function(object, data) ... end)`
- `get_name(object.tags)` calls → `theme.add_name(attrs, object)` before insert
- Remove `schema_name` and `srid` globals (handled by themepark options)
- Remove `require "helpers"` line (helpers are on `theme` via init.lua)

- [x] `topics/natural.lua` (point, line, polygon — good reference topic, do first)
- [x] `topics/water.lua` (point, line, polygon)
- [x] `topics/landuse.lua`
- [x] `topics/leisure.lua`
- [x] `topics/amenity.lua`
- [x] `topics/building.lua` (uses building helpers)
- [x] `topics/building_combined_point.lua`
- [x] `topics/indoor.lua`
- [x] `topics/infrastructure.lua`
- [x] `topics/place.lua` (note: nested polygon SQL is out of scope)
- [x] `topics/poi.lua` (uses poi helpers)
- [x] `topics/poi_combined_point.lua`
- [x] `topics/public_transport.lua`
- [x] `topics/road.lua` (point, line, polygon; uses routable_* helpers)
- [x] `topics/road_major.lua`
- [x] `topics/shop.lua` (uses shop helpers)
- [x] `topics/shop_combined_point.lua`
- [x] `topics/traffic.lua`
- [x] `topics/tags.lua` (ids_type='any', no geometry column)
- [x] `topics/unitable.lua` (ids_type='any', geometry type='geometry')

## Phase 4: Config Files

- [x] Create `config/default.lua`
  Topics: amenity, building, indoor, infrastructure, landuse, leisure, natural, place,
  poi, public_transport, road, shop, tags, traffic, water

- [x] Create `config/minimal.lua`
  Topics: place, poi_combined_point, road_major

- [x] Create `config/basic.lua`
  Topics: building_combined_point, landuse, place, poi_combined_point, road_major, unitable

- [x] Create `config/everything.lua`
  Topics: all 20 topics

  All four configs:
  - Load themepark
  - Set schema from `PGOSM_SCHEMA` env var (default: `'osm'`)
  - Set srid from `PGOSM_SRID` env var (default: `3857`)
  - Resolve theme dir from `PGOSM_THEME_DIR` → `$CONDA_PREFIX/share/pgosm-themepark/themes` → `../themes`
  - Load `core/name-with-fallback` **before** any pgosm topics

## Phase 5: Conda Packaging

- [x] Verify `osm2pgsql-themepark` on gis-forge sets `LUA_PATH` via its own activation
  mechanism (inspect installed package's `etc/conda/` directory). If it does not, an
  additional activation script will be needed — note this as a blocker before proceeding.

- [x] Create `recipe.yaml` (rattler-build v1)

## Phase 6: Verify

- [ ] Run `osm2pgsql --version` and confirm Themepark support is present

- [ ] Test `config/default.lua` against a small PBF (e.g., a city extract):
  ```sh
  osm2pgsql -d testdb -O flex \
    -S pgosm-themepark/config/default.lua \
    test.osm.pbf
  ```
  Confirm tables are created in the `osm` schema with expected columns.

- [ ] Test `config/minimal.lua` and `config/everything.lua`

- [ ] Build conda package locally:
  ```sh
  rattler-build build --recipe pgosm-themepark/recipe.yaml
  ```

- [ ] Install from local build and re-run test using `$CONDA_PREFIX` path:
  ```sh
  conda install --use-local pgosm-themepark
  osm2pgsql -d testdb -O flex \
    -S $CONDA_PREFIX/share/pgosm-themepark/config/default.lua \
    test.osm.pbf
  ```
