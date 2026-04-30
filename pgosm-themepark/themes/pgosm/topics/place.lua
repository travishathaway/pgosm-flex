-- ---------------------------------------------------------------------------
--
-- Theme: pgosm
-- Topic: place
--
-- Tables: place_point, place_line, place_polygon
--
-- Note: place_polygon_nested calculation (post-import SQL) is out of scope.
--
-- ---------------------------------------------------------------------------

local themepark, theme, cfg = ...

local place_cols = {
    { column = 'osm_type',    type = 'text', not_null = true },
    { column = 'boundary',    type = 'text' },
    { column = 'admin_level', type = 'int4' },
}

-- ---------------------------------------------------------------------------

themepark:add_table({
    name = 'place_point',
    ids_type = 'node',
    geom = 'point',
    columns = themepark:columns('core/name', place_cols),
    indexes = {
        { column = 'geom',        method = 'gist' },
        { column = 'osm_type',    method = 'btree' },
        { column = 'admin_level', method = 'btree' },
    },
})

themepark:add_table({
    name = 'place_line',
    ids_type = 'way',
    geom = 'linestring',
    columns = themepark:columns('core/name', place_cols),
    indexes = {
        { column = 'geom',        method = 'gist' },
        { column = 'osm_type',    method = 'btree' },
        { column = 'admin_level', method = 'btree' },
    },
})

themepark:add_table({
    name = 'place_polygon',
    ids_type = 'area',
    geom = 'multipolygon',
    columns = themepark:columns('core/name', {
        { column = 'osm_type',    type = 'text', not_null = true },
        { column = 'boundary',    type = 'text' },
        { column = 'admin_level', type = 'int4' },
        { column = 'member_ids',  type = 'jsonb' },
    }),
    indexes = {
        { column = 'geom',        method = 'gist' },
        { column = 'osm_type',    method = 'btree' },
        { column = 'admin_level', method = 'btree' },
    },
})

-- ---------------------------------------------------------------------------

local function get_osm_type(object)
    if object.tags.place then return object:grab_tag('place')
    elseif object.tags.boundary then return 'boundary'
    elseif object.tags.admin_level then return 'admin_level'
    end
    return nil
end

local function has_place_tags(tags)
    return tags.place or tags.boundary or tags.admin_level
end

themepark:add_proc('node', function(object, data)
    if not has_place_tags(object.tags) then return end
    local osm_type = get_osm_type(object)
    if not osm_type then return end
    local a = {
        osm_type    = osm_type,
        boundary    = object:grab_tag('boundary'),
        admin_level = theme.parse_admin_level(object:grab_tag('admin_level')),
        geom        = object:as_point(),
    }
    theme.add_name(a, object)
    themepark:insert('place_point', a)
end)

themepark:add_proc('way', function(object, data)
    if not has_place_tags(object.tags) then return end
    local osm_type = get_osm_type(object)
    if not osm_type then return end
    local boundary    = object:grab_tag('boundary')
    local admin_level = theme.parse_admin_level(object:grab_tag('admin_level'))
    local a = { osm_type = osm_type, boundary = boundary, admin_level = admin_level }
    theme.add_name(a, object)
    if object.is_closed then
        a.geom = object:as_polygon()
        themepark:insert('place_polygon', a)
    else
        a.geom = object:as_linestring()
        themepark:insert('place_line', a)
    end
end)

themepark:add_proc('relation', function(object, data)
    if not has_place_tags(object.tags) then return end
    local osm_type = get_osm_type(object)
    if not osm_type then return end
    local member_ids = osm2pgsql.way_member_ids(object)
    local a = {
        osm_type    = osm_type,
        boundary    = object:grab_tag('boundary'),
        admin_level = theme.parse_admin_level(object:grab_tag('admin_level')),
        member_ids  = member_ids,
        geom        = object:as_multipolygon(),
    }
    theme.add_name(a, object)
    themepark:insert('place_polygon', a)
end)

-- ---------------------------------------------------------------------------
