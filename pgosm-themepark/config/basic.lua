-- ---------------------------------------------------------------------------
--
-- pgosm-themepark config: basic
--
-- Layerset: building_combined_point, landuse, place, poi_combined_point,
--           road_major, unitable
--
-- Runtime env vars (all optional):
--   PGOSM_SCHEMA      - PostgreSQL schema name (default: osm)
--   PGOSM_SRID        - Spatial reference ID (default: 3857)
--   PGOSM_THEME_DIR   - Override theme search path
--
-- ---------------------------------------------------------------------------

local themepark = require('themepark')

themepark:set_option('schema', os.getenv('PGOSM_SCHEMA') or 'osm')
themepark:set_option('srid',   tonumber(os.getenv('PGOSM_SRID')) or 3857)

local conda_prefix = os.getenv('CONDA_PREFIX')
local theme_dir = os.getenv('PGOSM_THEME_DIR')
    or (conda_prefix and conda_prefix .. '/share/pgosm-themepark/themes')
    or '../themes'
themepark:add_theme_dir(theme_dir)

-- Name handling: load core/name-with-fallback BEFORE any pgosm topics
themepark:add_topic('core/name-with-fallback', {
    keys = { name = { 'name', 'short_name', 'alt_name', 'loc_name', 'old_name' } }
})

themepark:add_topic('pgosm/building_combined_point')
themepark:add_topic('pgosm/landuse')
themepark:add_topic('pgosm/place')
themepark:add_topic('pgosm/poi_combined_point')
themepark:add_topic('pgosm/road_major')
themepark:add_topic('pgosm/unitable')
