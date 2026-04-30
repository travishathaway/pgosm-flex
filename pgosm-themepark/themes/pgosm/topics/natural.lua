-- ---------------------------------------------------------------------------
--
-- Theme: pgosm
-- Topic: natural
--
-- Tables: natural_point, natural_line, natural_polygon
--
-- ---------------------------------------------------------------------------

local themepark, theme, cfg = ...

local water_natural_values = {
    'water', 'lake', 'hot_spring', 'waterfall', 'wetland',
    'swamp', 'water_meadow', 'waterway', 'spring'
}
local is_water_natural = theme.make_check_in_list_func(water_natural_values)

-- ---------------------------------------------------------------------------

themepark:add_table({
    name = 'natural_point',
    ids_type = 'node',
    geom = 'point',
    columns = themepark:columns('core/name', {
        { column = 'osm_type', type = 'text', not_null = true },
        { column = 'ele',      type = 'int' },
    }),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

themepark:add_table({
    name = 'natural_line',
    ids_type = 'way',
    geom = 'linestring',
    columns = themepark:columns('core/name', {
        { column = 'osm_type', type = 'text', not_null = true },
        { column = 'ele',      type = 'int' },
    }),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

themepark:add_table({
    name = 'natural_polygon',
    ids_type = 'way',
    geom = 'multipolygon',
    columns = themepark:columns('core/name', {
        { column = 'osm_type', type = 'text', not_null = true },
        { column = 'ele',      type = 'int' },
    }),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

-- ---------------------------------------------------------------------------

themepark:add_proc('node', function(object, data)
    if not object.tags.natural then return end
    -- Water-related natural values are handled by the water topic
    if is_water_natural(object.tags.natural) then return end

    local a = {
        osm_type = object:grab_tag('natural'),
        ele      = theme.parse_to_meters(object.tags.ele),
        geom     = object:as_point(),
    }
    theme.add_name(a, object)
    themepark:insert('natural_point', a)
end)

themepark:add_proc('way', function(object, data)
    if not object.tags.natural then return end
    if is_water_natural(object.tags.natural) then return end

    local a = {
        osm_type = object:grab_tag('natural'),
        ele      = theme.parse_to_meters(object.tags.ele),
    }
    theme.add_name(a, object)

    if object.is_closed then
        a.geom = object:as_polygon()
        themepark:insert('natural_polygon', a)
    else
        a.geom = object:as_linestring()
        themepark:insert('natural_line', a)
    end
end)

-- ---------------------------------------------------------------------------
