-- ---------------------------------------------------------------------------
--
-- Theme: pgosm
-- Topic: landuse
--
-- Tables: landuse_point, landuse_polygon
--
-- ---------------------------------------------------------------------------

local themepark, theme, cfg = ...

-- ---------------------------------------------------------------------------

themepark:add_table({
    name = 'landuse_point',
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
    name = 'landuse_polygon',
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
    if not object.tags.landuse then return end
    local a = { osm_type = object:grab_tag('landuse'), geom = object:as_point() }
    theme.add_name(a, object)
    themepark:insert('landuse_point', a)
end)

themepark:add_proc('way', function(object, data)
    if not object.tags.landuse then return end
    if not object.is_closed then return end
    local a = { osm_type = object:grab_tag('landuse'), geom = object:as_polygon() }
    theme.add_name(a, object)
    themepark:insert('landuse_polygon', a)
end)

themepark:add_proc('relation', function(object, data)
    if not object.tags.landuse then return end
    if object.tags.type == 'multipolygon' or object.tags.type == 'boundary' then
        local a = { osm_type = object:grab_tag('landuse'), geom = object:as_multipolygon() }
        theme.add_name(a, object)
        themepark:insert('landuse_polygon', a)
    end
end)

-- ---------------------------------------------------------------------------
