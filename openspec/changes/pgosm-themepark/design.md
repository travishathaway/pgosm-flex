# Design: pgosm-themepark

## Directory Layout

```
pgosm-themepark/
├── recipe.yaml
├── themes/
│   └── pgosm/
│       ├── init.lua
│       └── topics/
│           ├── amenity.lua
│           ├── building.lua
│           ├── building_combined_point.lua
│           ├── indoor.lua
│           ├── infrastructure.lua
│           ├── landuse.lua
│           ├── leisure.lua
│           ├── natural.lua
│           ├── place.lua
│           ├── poi.lua
│           ├── poi_combined_point.lua
│           ├── public_transport.lua
│           ├── road.lua
│           ├── road_major.lua
│           ├── shop.lua
│           ├── shop_combined_point.lua
│           ├── tags.lua
│           ├── traffic.lua
│           ├── unitable.lua
│           └── water.lua
└── config/
    ├── default.lua
    ├── minimal.lua
    ├── basic.lua
    └── everything.lua
```

## Theme Init (`themes/pgosm/init.lua`)

The init file is loaded once when the theme is first used. It exposes all shared helper functions on the `theme` table so topics can access them via `theme.<func>()`. It does **not** set global variables.

Functions migrated from `helpers.lua` and the three `*_helpers.lua` files:

| Source file | Functions |
|---|---|
| `helpers.lua` | `parse_to_meters`, `parse_speed`, `parse_layer_value`, `major_road`, `starts_with`, `ends_with`, `get_ref`, `parse_admin_level`, `get_address`, `get_wheelchair_desc`, `routable_foot`, `routable_cycle`, `routable_motor` |
| `building_helpers.lua` | `is_first_level_building`, `address_only_building`, `get_osm_type_subtype_building` |
| `poi_helpers.lua` | `get_poi_osm_type_subtype`, POI classification helpers |
| `shop_helpers.lua` | `get_shop_osm_type_subtype`, shop classification helpers |

The `get_name()` function and language handling are **not** migrated — those are replaced by Themepark's `core/name-with-fallback`.

## Name Handling

Name handling is delegated to Themepark's `core` theme. The config files load one name topic which sets the policy for all topics:

```lua
themepark:add_topic('core/name-with-fallback', {
    keys = {
        name = { 'name', 'short_name', 'alt_name', 'loc_name', 'old_name' }
    }
})
```

Every topic table that carries a name column uses `themepark:columns('core/name', { ... })` to inject the name column. This replaces all `get_name()` calls in topic processing functions — instead, `theme.add_name(attrs, object)` is called before insert.

Language-specific fallback (formerly `pgosm_language`) is configured per config file. For example a multilingual config could do:

```lua
themepark:add_topic('core/name-with-fallback', {
    keys = {
        name = { 'name:en', 'name', 'short_name', 'alt_name' }
    }
})
```

## Topic File Pattern

Each topic follows this structure:

```lua
-- topics/natural.lua
local themepark, theme, cfg = ...

-- Table definitions
themepark:add_table({
    name = 'natural_point',
    ids_type = 'node',
    geom = 'point',
    columns = themepark:columns('core/name', {
        { column = 'osm_type', type = 'text', not_null = true },
        { column = 'ele',      type = 'int' },
    }),
    indexes = {
        { column = 'geom', method = 'gist' },
    }
})

-- Processing functions (no chaining boilerplate)
themepark:add_proc('node', function(object, data)
    if not object.tags.natural then return end
    local a = {
        osm_type = object.tags.natural,
        ele      = theme.parse_to_meters(object.tags.ele),
        geom     = object:as_point(),
    }
    theme.add_name(a, object)
    themepark:insert('natural_point', a)
end)
```

Key differences from the current style:
- `osm2pgsql.define_table()` → `themepark:add_table()`
- `schema_name` global → removed; schema set via `themepark:set_option('schema', ...)`
- `srid` global → removed; srid set via `themepark:set_option('srid', ...)`
- `get_name()` + global language var → `theme.add_name(attrs, object)` + `themepark:columns('core/name', ...)`
- Manual process_node/way/relation chaining → `themepark:add_proc('node'/'way'/'relation', func)`
- `deep_copy()` → not needed; Themepark handles dispatch safely
- `get_indexes_from_spec()` + INI files → `indexes = { ... }` inline in `add_table()`

## Index Strategy

The INI-driven index system is dropped entirely. Each topic defines sensible default indexes inline:

- All geometry columns: `{ column = 'geom', method = 'gist' }`
- `osm_type` where it is frequently filtered: `{ column = 'osm_type', method = 'btree' }`
- No other indexes by default (users can add custom indexes post-import if needed)

This matches the behavior of the `indexes/` defaults (not the `lotsofindexes` variant).

## Config Files

Four config files, one per layerset. Each config:

1. Requires themepark
2. Sets schema and srid from environment variables with sensible defaults
3. Adds theme search path pointing to the conda prefix (with fallback for local dev)
4. Loads the name topic
5. Loads the appropriate set of pgosm topics

```lua
-- config/default.lua
local themepark = require('themepark')

themepark:set_option('schema', os.getenv('PGOSM_SCHEMA') or 'osm')
themepark:set_option('srid',   tonumber(os.getenv('PGOSM_SRID')) or 3857)

local conda_prefix = os.getenv('CONDA_PREFIX')
local theme_dir = os.getenv('PGOSM_THEME_DIR')
    or (conda_prefix and conda_prefix .. '/share/pgosm-themepark/themes')
    or '../themes'
themepark:add_theme_dir(theme_dir)

themepark:add_topic('core/name-with-fallback', {
    keys = { name = { 'name', 'short_name', 'alt_name', 'loc_name', 'old_name' } }
})

-- default layerset topics
themepark:add_topic('pgosm/amenity')
themepark:add_topic('pgosm/building')
themepark:add_topic('pgosm/indoor')
themepark:add_topic('pgosm/infrastructure')
themepark:add_topic('pgosm/landuse')
themepark:add_topic('pgosm/leisure')
themepark:add_topic('pgosm/natural')
themepark:add_topic('pgosm/place')
themepark:add_topic('pgosm/poi')
themepark:add_topic('pgosm/public_transport')
themepark:add_topic('pgosm/road')
themepark:add_topic('pgosm/shop')
themepark:add_topic('pgosm/tags')
themepark:add_topic('pgosm/traffic')
themepark:add_topic('pgosm/water')
```

Layerset topic sets (derived from existing INI files):

| Topic | minimal | basic | default | everything |
|---|---|---|---|---|
| amenity | | | ✓ | ✓ |
| building | | | ✓ | ✓ |
| building_combined_point | | ✓ | | ✓ |
| indoor | | | ✓ | ✓ |
| infrastructure | | | ✓ | ✓ |
| landuse | | ✓ | ✓ | ✓ |
| leisure | | | ✓ | ✓ |
| natural | | | ✓ | ✓ |
| place | ✓ | ✓ | ✓ | ✓ |
| poi | | | ✓ | ✓ |
| poi_combined_point | ✓ | ✓ | | ✓ |
| public_transport | | | ✓ | ✓ |
| road | | | ✓ | ✓ |
| road_major | ✓ | ✓ | | ✓ |
| shop | | | ✓ | ✓ |
| shop_combined_point | | | | ✓ |
| tags | | | ✓ | ✓ |
| traffic | | | ✓ | ✓ |
| unitable | | ✓ | | ✓ |
| water | | | ✓ | ✓ |

## Conda Recipe (`recipe.yaml`)

Rattler-build v1 format. The package depends on `osm2pgsql-themepark` (from gis-forge) at runtime so that the Themepark Lua framework is available on `LUA_PATH` (set by that package's own activation mechanism).

```yaml
package:
  name: pgosm-themepark
  version: "0.1.0"

source:
  path: .

build:
  number: 0
  script:
    - mkdir -p $PREFIX/share/pgosm-themepark/themes
    - mkdir -p $PREFIX/share/pgosm-themepark/config
    - mkdir -p $PREFIX/etc/conda/env_vars.d
    - cp -r themes/ $PREFIX/share/pgosm-themepark/themes/
    - cp -r config/ $PREFIX/share/pgosm-themepark/config/
    - cat > $PREFIX/etc/conda/env_vars.d/pgosm-themepark.json << EOF
      {
        "THEMEPARK_PATH": "$PREFIX/share/pgosm-themepark/themes"
      }
      EOF

requirements:
  run:
    - osm2pgsql-themepark

test:
  commands:
    - test -f $PREFIX/share/pgosm-themepark/themes/pgosm/init.lua
    - test -f $PREFIX/share/pgosm-themepark/config/default.lua
    - test -f $PREFIX/etc/conda/env_vars.d/pgosm-themepark.json
```

## Environment Variables (`env_vars.d`)

Rather than shell activation scripts, environment variables are set via a JSON file at
`$PREFIX/etc/conda/env_vars.d/pgosm-themepark.json`. This is more portable and efficient
than shell scripts — no arbitrary code execution, no shell-specific branching.

Only one variable is needed:

| Variable | Value | Purpose |
|---|---|---|
| `THEMEPARK_PATH` | `$PREFIX/share/pgosm-themepark/themes` | Tells the Themepark framework where to find the `pgosm` theme |

**`LUA_PATH` is not set here.** That is the responsibility of the `osm2pgsql-themepark`
dependency, which sets it to include its own Lua framework files via its own activation
mechanism. The separation of concerns is:

```
osm2pgsql-themepark  →  sets LUA_PATH  (framework Lua files)
pgosm-themepark      →  sets THEMEPARK_PATH  (pgosm theme files)
```

The `$PREFIX` value is expanded at **build time** (unquoted heredoc), so the baked-in
path matches the install prefix. rattler-build replaces the placeholder prefix at
install time, so the path remains correct regardless of where the env is installed.

## Runtime Usage (After Install)

```sh
conda install -c gis-forge pgosm-themepark

# Schema and SRID are optional — defaults are 'osm' and 3857
export PGOSM_SCHEMA=osm
export PGOSM_SRID=3857

osm2pgsql -d mydb -O flex \
  -S $CONDA_PREFIX/share/pgosm-themepark/config/default.lua \
  myregion.osm.pbf
```

## Open Questions / Known Risks

1. **`LUA_PATH` set by `osm2pgsql-themepark`** — this design assumes the `osm2pgsql-themepark` gis-forge package sets `LUA_PATH` via its own activation mechanism. This must be verified by inspecting the installed package before implementation. If it does not, an activation script (`.sh`) will need to be added in addition to the JSON file, since `env_vars.d` JSON only supports simple key=value and cannot prepend to an existing path variable.

2. **`core/name-with-fallback` column injection** — topics that use `themepark:columns('core/name', {...})` require `core/name-with-fallback` (or another `core/name-*` topic) to have been loaded first. Config files must load the name topic before any pgosm topics.

3. **`tags` and `unitable` topics** — these topics use `ids_type = 'any'` and geometry type `'geometry'` (not a specific type). The `themepark:add_table` `geom` parameter for these needs to be verified against the Themepark docs for the `any` geometry type.

4. **`place` topic nested polygon SQL** — `sql/place_polygon_nested.sql` is excluded from scope but is used post-import. This is an acceptable gap for v1 since it is post-processing, not part of flex config.
