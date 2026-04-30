-- ---------------------------------------------------------------------------
--
-- Theme: pgosm
-- Topic: leisure
--
-- Tables: leisure_point, leisure_polygon
--
-- ---------------------------------------------------------------------------

local themepark, theme, cfg = ...

-- ---------------------------------------------------------------------------

themepark:add_table({
    name = 'leisure_point',
    ids_type = 'node',
    geom = 'point',
    columns = themepark:columns('core/name', {
        { column = 'osm_type', type = 'text', not_null = true },
    }),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

themepark:add_table({
    name = 'leisure_polygon',
    ids_type = 'way',
    geom = 'multipolygon',
    columns = themepark:columns('core/name', {
        { column = 'osm_type', type = 'text', not_null = true },
    }),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

-- ---------------------------------------------------------------------------

themepark:add_proc('node', function(object, data)
    if not object.tags.leisure then return end
    local a = { osm_type = object:grab_tag('leisure'), geom = object:as_point() }
    theme.add_name(a, object)
    themepark:insert('leisure_point', a)
end)

themepark:add_proc('way', function(object, data)
    if not object.tags.leisure then return end
    if not object.is_closed then return end
    local a = { osm_type = object:grab_tag('leisure'), geom = object:as_polygon() }
    theme.add_name(a, object)
    themepark:insert('leisure_polygon', a)
end)

-- ---------------------------------------------------------------------------
