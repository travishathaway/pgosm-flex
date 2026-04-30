-- ---------------------------------------------------------------------------
--
-- Theme: pgosm
-- Topic: water
--
-- Tables: water_point, water_line, water_polygon
--
-- ---------------------------------------------------------------------------

local themepark, theme, cfg = ...

local water_natural_values = {
    'water', 'lake', 'hot_spring', 'waterfall', 'wetland',
    'swamp', 'water_meadow', 'waterway', 'spring'
}

-- ---------------------------------------------------------------------------

themepark:add_table({
    name = 'water_point',
    ids_type = 'node',
    geom = 'point',
    columns = themepark:columns('core/name', {
        { column = 'osm_type',    type = 'text', not_null = true },
        { column = 'osm_subtype', type = 'text', not_null = true },
        { column = 'layer',       type = 'int',  not_null = true },
        { column = 'tunnel',      type = 'text' },
        { column = 'bridge',      type = 'text' },
        { column = 'boat',        type = 'text' },
    }),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

themepark:add_table({
    name = 'water_line',
    ids_type = 'way',
    geom = 'multilinestring',
    columns = themepark:columns('core/name', {
        { column = 'osm_type',    type = 'text', not_null = true },
        { column = 'osm_subtype', type = 'text', not_null = true },
        { column = 'layer',       type = 'int',  not_null = true },
        { column = 'tunnel',      type = 'text' },
        { column = 'bridge',      type = 'text' },
        { column = 'boat',        type = 'text' },
        { column = 'member_ids',  type = 'jsonb' },
    }),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

themepark:add_table({
    name = 'water_polygon',
    ids_type = 'way',
    geom = 'multipolygon',
    columns = themepark:columns('core/name', {
        { column = 'osm_type',    type = 'text', not_null = true },
        { column = 'osm_subtype', type = 'text', not_null = true },
        { column = 'layer',       type = 'int',  not_null = true },
        { column = 'tunnel',      type = 'text' },
        { column = 'bridge',      type = 'text' },
        { column = 'boat',        type = 'text' },
        { column = 'member_ids',  type = 'jsonb' },
    }),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

-- ---------------------------------------------------------------------------

local function is_water_natural(natural_tag)
    for _, v in ipairs(water_natural_values) do
        if natural_tag == v then return true end
    end
    return false
end

local function process_water_object_node(object)
    local osm_type, osm_subtype
    if object.tags.natural and is_water_natural(object.tags.natural) then
        osm_type = 'natural'
        osm_subtype = object:grab_tag('natural')
    elseif object.tags.waterway then
        osm_type = 'waterway'
        osm_subtype = object:grab_tag('waterway')
    else
        return nil
    end
    return {
        osm_type    = osm_type,
        osm_subtype = osm_subtype,
        layer       = theme.parse_layer_value(object.tags.layer),
        tunnel      = object:grab_tag('tunnel'),
        bridge      = object:grab_tag('bridge'),
        boat        = object:grab_tag('boat'),
    }
end

-- ---------------------------------------------------------------------------

themepark:add_proc('node', function(object, data)
    if not object.tags.natural and not object.tags.waterway then return end
    local a = process_water_object_node(object)
    if not a then return end
    a.geom = object:as_point()
    theme.add_name(a, object)
    themepark:insert('water_point', a)
end)

themepark:add_proc('way', function(object, data)
    if not object.tags.natural and not object.tags.waterway then return end

    local osm_type, osm_subtype
    if object.tags.natural and is_water_natural(object.tags.natural) then
        osm_type = 'natural'
        osm_subtype = object:grab_tag('natural')
    elseif object.tags.waterway then
        osm_type = 'waterway'
        osm_subtype = object:grab_tag('waterway')
    else
        return
    end

    local a = {
        osm_type    = osm_type,
        osm_subtype = osm_subtype,
        layer       = theme.parse_layer_value(object.tags.layer),
        tunnel      = object:grab_tag('tunnel'),
        bridge      = object:grab_tag('bridge'),
        boat        = object:grab_tag('boat'),
    }
    theme.add_name(a, object)

    if object.is_closed then
        a.geom = object:as_polygon()
        themepark:insert('water_polygon', a)
    else
        a.geom = object:as_linestring()
        themepark:insert('water_line', a)
    end
end)

themepark:add_proc('relation', function(object, data)
    if not object.tags.natural and not object.tags.waterway then return end

    local osm_type, osm_subtype
    if object.tags.natural and is_water_natural(object.tags.natural) then
        osm_type = 'natural'
        osm_subtype = object:grab_tag('natural')
    elseif object.tags.waterway then
        osm_type = 'waterway'
        osm_subtype = object:grab_tag('waterway')
    else
        return
    end

    local member_ids = osm2pgsql.way_member_ids(object)
    local a = {
        osm_type    = osm_type,
        osm_subtype = osm_subtype,
        layer       = theme.parse_layer_value(object.tags.layer),
        tunnel      = object:grab_tag('tunnel'),
        bridge      = object:grab_tag('bridge'),
        boat        = object:grab_tag('boat'),
        member_ids  = member_ids,
    }
    theme.add_name(a, object)

    if object.tags.type == 'multipolygon' then
        a.geom = object:as_multipolygon()
        themepark:insert('water_polygon', a)
    else
        a.geom = object:as_multilinestring()
        themepark:insert('water_line', a)
    end
end)

-- ---------------------------------------------------------------------------
