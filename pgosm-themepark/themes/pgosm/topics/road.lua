-- ---------------------------------------------------------------------------
--
-- Theme: pgosm
-- Topic: road
--
-- Tables: road_point, road_line, road_polygon
--
-- ---------------------------------------------------------------------------

local themepark, theme, cfg = ...

local road_cols_shared = {
    { column = 'osm_type',  type = 'text', not_null = true },
    { column = 'ref',       type = 'text' },
    { column = 'maxspeed',  type = 'int' },
    { column = 'layer',     type = 'int', not_null = true },
    { column = 'tunnel',    type = 'text' },
    { column = 'bridge',    type = 'text' },
    { column = 'access',    type = 'text' },
}

-- ---------------------------------------------------------------------------

themepark:add_table({
    name = 'road_point',
    ids_type = 'node',
    geom = 'point',
    columns = themepark:columns('core/name', {
        { column = 'osm_type', type = 'text', not_null = true },
        { column = 'ref',      type = 'text' },
        { column = 'maxspeed', type = 'int' },
        { column = 'oneway',   type = 'direction' },
        { column = 'layer',    type = 'int', not_null = true },
        { column = 'tunnel',   type = 'text' },
        { column = 'bridge',   type = 'text' },
        { column = 'access',   type = 'text' },
    }),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

themepark:add_table({
    name = 'road_line',
    ids_type = 'way',
    geom = 'multilinestring',
    columns = themepark:columns('core/name', {
        { column = 'osm_type',    type = 'text',    not_null = true },
        { column = 'ref',         type = 'text' },
        { column = 'maxspeed',    type = 'int' },
        { column = 'oneway',      type = 'direction' },
        { column = 'layer',       type = 'int',     not_null = true },
        { column = 'tunnel',      type = 'text' },
        { column = 'bridge',      type = 'text' },
        { column = 'major',       type = 'boolean', not_null = true },
        { column = 'route_foot',  type = 'boolean' },
        { column = 'route_cycle', type = 'boolean' },
        { column = 'route_motor', type = 'boolean' },
        { column = 'access',      type = 'text' },
        { column = 'member_ids',  type = 'jsonb' },
    }),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

themepark:add_table({
    name = 'road_polygon',
    ids_type = 'way',
    geom = 'multipolygon',
    columns = themepark:columns('core/name', {
        { column = 'osm_type',    type = 'text',    not_null = true },
        { column = 'ref',         type = 'text' },
        { column = 'maxspeed',    type = 'int' },
        { column = 'layer',       type = 'int',     not_null = true },
        { column = 'tunnel',      type = 'text' },
        { column = 'bridge',      type = 'text' },
        { column = 'major',       type = 'boolean', not_null = true },
        { column = 'route_foot',  type = 'boolean' },
        { column = 'route_cycle', type = 'boolean' },
        { column = 'route_motor', type = 'boolean' },
        { column = 'access',      type = 'text' },
        { column = 'member_ids',  type = 'jsonb' },
    }),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

-- ---------------------------------------------------------------------------

themepark:add_proc('node', function(object, data)
    if not object.tags.highway then return end
    local a = {
        osm_type = object.tags.highway,
        ref      = theme.get_ref(object.tags),
        maxspeed = theme.parse_speed(object.tags.maxspeed),
        oneway   = object.tags.oneway or 0,
        layer    = theme.parse_layer_value(object.tags.layer),
        tunnel   = object.tags.tunnel,
        bridge   = object.tags.bridge,
        access   = object.tags.access,
        geom     = object:as_point(),
    }
    theme.add_name(a, object)
    themepark:insert('road_point', a)
end)

themepark:add_proc('way', function(object, data)
    if not object.tags.highway then return end
    local osm_type = object.tags.highway
    local a = {
        osm_type    = osm_type,
        ref         = theme.get_ref(object.tags),
        maxspeed    = theme.parse_speed(object.tags.maxspeed),
        layer       = theme.parse_layer_value(object.tags.layer),
        tunnel      = object.tags.tunnel,
        bridge      = object.tags.bridge,
        major       = theme.major_road(osm_type),
        route_foot  = theme.routable_foot(object.tags),
        route_cycle = theme.routable_cycle(object.tags),
        route_motor = theme.routable_motor(object.tags),
        access      = object.tags.access,
    }
    theme.add_name(a, object)
    if object.tags.area == 'yes' or object.tags.indoor == 'room' then
        a.geom = object:as_polygon()
        themepark:insert('road_polygon', a)
    else
        a.oneway = object.tags.oneway or 0
        a.geom = object:as_linestring()
        themepark:insert('road_line', a)
    end
end)

themepark:add_proc('relation', function(object, data)
    if not object.tags.highway then return end
    local osm_type = object.tags.highway
    local member_ids = osm2pgsql.way_member_ids(object)
    local a = {
        osm_type    = osm_type,
        ref         = theme.get_ref(object.tags),
        maxspeed    = theme.parse_speed(object.tags.maxspeed),
        layer       = theme.parse_layer_value(object.tags.layer),
        tunnel      = object.tags.tunnel,
        bridge      = object.tags.bridge,
        major       = theme.major_road(osm_type),
        route_foot  = theme.routable_foot(object.tags),
        route_cycle = theme.routable_cycle(object.tags),
        route_motor = theme.routable_motor(object.tags),
        access      = object.tags.access,
        member_ids  = member_ids,
    }
    theme.add_name(a, object)
    if object.tags.area == 'yes' or object.tags.indoor == 'room' then
        a.geom = object:as_multipolygon()
        themepark:insert('road_polygon', a)
    else
        a.oneway = object.tags.oneway or 0
        a.geom = object:as_multilinestring()
        themepark:insert('road_line', a)
    end
end)

-- ---------------------------------------------------------------------------
