-- ---------------------------------------------------------------------------
--
-- pgosm-themepark config: default
--
-- Layerset: amenity, building, indoor, infrastructure, landuse, leisure,
--           natural, place, poi, public_transport, road, shop, tags,
--           traffic, water
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
