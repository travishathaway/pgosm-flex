# Proposal: pgosm-themepark

## What

Create a standalone `pgosm-themepark` package — a new subdirectory within this repository — that ports the existing OSM layer definitions from `pgosm_flex/flex-config/` into the [osm2pgsql Themepark](https://osm2pgsql.org/themepark/) framework and packages them as a conda package installable from the `gis-forge` channel.

The deliverable is a self-contained directory:

```
pgosm-themepark/
├── recipe.yaml              ← conda-build v1 recipe
├── themes/
│   └── pgosm/
│       ├── init.lua         ← shared helpers (formerly helpers.lua + *_helpers.lua)
│       └── topics/          ← 20 topic files, one per OSM layer
└── config/
    ├── default.lua          ← generated Lua entry-point configs
    ├── minimal.lua
    ├── basic.lua
    └── everything.lua
```

## Why

**Current pain:** The flex-config directory is tightly coupled to the `pgosm-flex` Python application. Using the Lua styles standalone requires cloning the whole repo, manually setting `PGOSM_LUA_CONFIG`, and wiring together the topic chaining by hand. There is no way to `conda install` the styles and use them directly with `osm2pgsql`.

**The opportunity:** The existing topic structure (one `.lua` per OSM theme — building, natural, road, etc.) maps almost perfectly onto Themepark's `theme/topic` model. The migration is largely mechanical, and adopting Themepark buys:

1. **Elimination of boilerplate** — the manual deep-copy + callback chaining pattern (~10 lines per processor per topic, across 20 topics) is replaced by `themepark:add_proc()`.
2. **Native name handling** — `core/name-with-fallback` replaces the bespoke `get_name()` / `pgosm_language` env-var mechanism with Themepark's composable naming policy.
3. **Conda installability** — users can `conda install -c gis-forge pgosm-themepark` and immediately point `osm2pgsql -S` at a config file in `$CONDA_PREFIX/share/pgosm-themepark/config/`.
4. **Independence from pgosm-flex Python** — the Themepark package becomes a standalone artifact. The existing Python application can later adapt to depend on it (option C), but this migration does not touch the Python application.

**Why now:** Themepark is the upstream-recommended approach for reusable flex configs. Staying on the hand-rolled chaining pattern accumulates divergence from the ecosystem.

## Scope

**In scope:**
- All 20 topics from `flex-config/style/`: amenity, building, building_combined_point, indoor, infrastructure, landuse, leisure, natural, place, poi, poi_combined_point, public_transport, road, road_major, shop, shop_combined_point, tags, traffic, unitable, water
- Four generated config files matching the existing layersets: default, minimal, basic, everything
- `themes/pgosm/init.lua` absorbing all shared helper functions
- `recipe.yaml` (rattler-build / conda-build v1 format) for conda packaging
- Conda activation scripts that set `LUA_PATH` and `THEMEPARK_PATH` on env activate/deactivate

**Out of scope:**
- Modifying the existing `pgosm_flex/flex-config/` directory (clean cut, no compatibility shim)
- Porting the `sql/` post-processing scripts (they are not part of osm2pgsql flex config)
- Modifying the Python `pgosm-flex` application to use the new package
- Publishing to conda-forge (gis-forge channel only for v1)

## Success Criteria

- `osm2pgsql -d mydb -O flex -S $CONDA_PREFIX/share/pgosm-themepark/config/default.lua myfile.osm.pbf` runs without error after `conda install -c gis-forge pgosm-themepark`
- All 20 topics produce the same table schemas as the current `flex-config/style/` equivalents
- No dependency on `PGOSM_LUA_CONFIG` or any pgosm-flex Python code
- `LUA_PATH` and `THEMEPARK_PATH` are set automatically by conda activation scripts
