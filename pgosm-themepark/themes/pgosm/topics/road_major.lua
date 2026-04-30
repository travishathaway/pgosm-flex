-- ---------------------------------------------------------------------------
--
-- Theme: pgosm
-- Topic: road_major
--
-- Table: road_major
-- Major roads only (motorway, primary, secondary, tertiary, trunk).
--
-- ---------------------------------------------------------------------------

local themepark, theme, cfg = ...

-- ---------------------------------------------------------------------------

themepark:add_table({
    name = 'road_major',
    ids_type = 'way',
    geom = 'multilinestring',
    columns = themepark:columns('core/name', {
        { column = 'osm_type',   type = 'text',    not_null = true },
        { column = 'ref',        type = 'text' },
        { column = 'maxspeed',   type = 'int' },
        { column = 'layer',      type = 'int',     not_null = true },
        { column = 'tunnel',     type = 'text' },
        { column = 'bridge',     type = 'text' },
        { column = 'major',      type = 'boolean', not_null = true },
        { column = 'member_ids', type = 'jsonb' },
    }),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

-- ---------------------------------------------------------------------------

themepark:add_proc('way', function(object, data)
    if not object.tags.highway then return end
    if not theme.major_road(object.tags.highway) then return end
    local a = {
        osm_type = object.tags.highway,
        ref      = theme.get_ref(object.tags),
        maxspeed = theme.parse_speed(object.tags.maxspeed),
        layer    = theme.parse_layer_value(object.tags.layer),
        tunnel   = object:grab_tag('tunnel'),
        bridge   = object:grab_tag('bridge'),
        major    = true,
        geom     = object:as_linestring(),
    }
    theme.add_name(a, object)
    themepark:insert('road_major', a)
end)

themepark:add_proc('relation', function(object, data)
    if not object.tags.highway then return end
    if not theme.major_road(object.tags.highway) then return end
    local a = {
        osm_type   = object.tags.highway,
        ref        = theme.get_ref(object.tags),
        maxspeed   = theme.parse_speed(object.tags.maxspeed),
        layer      = theme.parse_layer_value(object.tags.layer),
        tunnel     = object.tags.tunnel,
        bridge     = object.tags.bridge,
        major      = true,
        member_ids = osm2pgsql.way_member_ids(object),
        geom       = object:as_multilinestring(),
    }
    theme.add_name(a, object)
    themepark:insert('road_major', a)
end)

-- ---------------------------------------------------------------------------
