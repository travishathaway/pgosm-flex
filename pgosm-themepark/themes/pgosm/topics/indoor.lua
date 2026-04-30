-- ---------------------------------------------------------------------------
--
-- Theme: pgosm
-- Topic: indoor
--
-- Tables: indoor_point, indoor_line, indoor_polygon
--
-- ---------------------------------------------------------------------------

local themepark, theme, cfg = ...

local indoor_first_level_keys = { 'indoor', 'door', 'entrance' }
local is_first_level_indoor = theme.make_check_in_list_func(indoor_first_level_keys)

local function get_osm_type(object)
    if object.tags.indoor then return object.tags.indoor
    elseif object.tags.door then return 'door'
    elseif object.tags.entrance then return 'entrance'
    else return 'unknown'
    end
end

local indoor_cols = {
    { column = 'osm_type',  type = 'text', not_null = true },
    { column = 'layer',     type = 'int' },
    { column = 'level',     type = 'text' },
    { column = 'room',      type = 'text' },
    { column = 'entrance',  type = 'text' },
    { column = 'door',      type = 'text' },
    { column = 'capacity',  type = 'text' },
    { column = 'highway',   type = 'text' },
}

-- ---------------------------------------------------------------------------

themepark:add_table({
    name = 'indoor_point',
    ids_type = 'node',
    geom = 'point',
    columns = themepark:columns('core/name', indoor_cols),
    indexes = { { column = 'geom', method = 'gist' } },
})

themepark:add_table({
    name = 'indoor_line',
    ids_type = 'way',
    geom = 'linestring',
    columns = themepark:columns('core/name', indoor_cols),
    indexes = { { column = 'geom', method = 'gist' } },
})

themepark:add_table({
    name = 'indoor_polygon',
    ids_type = 'way',
    geom = 'multipolygon',
    columns = themepark:columns('core/name', indoor_cols),
    indexes = { { column = 'geom', method = 'gist' } },
})

-- ---------------------------------------------------------------------------

local function build_attrs(object)
    local a = {
        osm_type = get_osm_type(object),
        layer    = theme.parse_layer_value(object.tags.layer),
        level    = object.tags.level,
        room     = object.tags.room,
        entrance = object.tags.entrance,
        door     = object.tags.door,
        capacity = object.tags.capacity,
        highway  = object.tags.highway,
    }
    theme.add_name(a, object)
    return a
end

themepark:add_proc('node', function(object, data)
    if not is_first_level_indoor(object.tags) then return end
    local a = build_attrs(object)
    a.geom = object:as_point()
    themepark:insert('indoor_point', a)
end)

themepark:add_proc('way', function(object, data)
    if not is_first_level_indoor(object.tags) then return end
    local a = build_attrs(object)
    if object.is_closed then
        a.geom = object:as_polygon()
        themepark:insert('indoor_polygon', a)
    else
        a.geom = object:as_linestring()
        themepark:insert('indoor_line', a)
    end
end)

-- ---------------------------------------------------------------------------
