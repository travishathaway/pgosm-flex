-- ---------------------------------------------------------------------------
--
-- Theme: pgosm
-- Topic: public_transport
--
-- Tables: public_transport_point, public_transport_line, public_transport_polygon
--
-- ---------------------------------------------------------------------------

local themepark, theme, cfg = ...

local pt_first_level_keys = { 'public_transport', 'aerialway', 'railway' }
local is_first_level_pt = theme.make_check_in_list_func(pt_first_level_keys)

local function get_osm_type_subtype(object)
    local t = {}
    if object.tags.bus then
        t.osm_type = 'bus';          t.osm_subtype = object.tags.bus
    elseif object.tags.railway then
        t.osm_type = 'railway';      t.osm_subtype = object.tags.railway
    elseif object.tags.lightrail then
        t.osm_type = 'lightrail';    t.osm_subtype = object.tags.lightrail
    elseif object.tags.train then
        t.osm_type = 'train';        t.osm_subtype = object.tags.train
    elseif object.tags.aerialway then
        t.osm_type = 'aerialway';    t.osm_subtype = object.tags.aerialway
    elseif object.tags.highway then
        t.osm_type = 'highway';      t.osm_subtype = object.tags.highway
    else
        t.osm_type = object.tags.public_transport or 'unknown'
        t.osm_subtype = nil
    end
    return t
end

local pt_cols = {
    { column = 'osm_type',        type = 'text', not_null = true },
    { column = 'osm_subtype',     type = 'text' },
    { column = 'public_transport', type = 'text', not_null = true },
    { column = 'layer',           type = 'int',  not_null = true },
    { column = 'ref',             type = 'text' },
    { column = 'operator',        type = 'text' },
    { column = 'network',         type = 'text' },
    { column = 'surface',         type = 'text' },
    { column = 'bus',             type = 'text' },
    { column = 'shelter',         type = 'text' },
    { column = 'bench',           type = 'text' },
    { column = 'lit',             type = 'text' },
    { column = 'wheelchair',      type = 'text' },
    { column = 'wheelchair_desc', type = 'text' },
}

-- ---------------------------------------------------------------------------

themepark:add_table({
    name = 'public_transport_point',
    ids_type = 'node',
    geom = 'point',
    columns = themepark:columns('core/name', pt_cols),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

themepark:add_table({
    name = 'public_transport_line',
    ids_type = 'way',
    geom = 'multilinestring',
    columns = themepark:columns('core/name', {
        { column = 'osm_type',        type = 'text', not_null = true },
        { column = 'osm_subtype',     type = 'text' },
        { column = 'public_transport', type = 'text', not_null = true },
        { column = 'layer',           type = 'int',  not_null = true },
        { column = 'ref',             type = 'text' },
        { column = 'operator',        type = 'text' },
        { column = 'network',         type = 'text' },
        { column = 'surface',         type = 'text' },
        { column = 'bus',             type = 'text' },
        { column = 'shelter',         type = 'text' },
        { column = 'bench',           type = 'text' },
        { column = 'lit',             type = 'text' },
        { column = 'wheelchair',      type = 'text' },
        { column = 'wheelchair_desc', type = 'text' },
        { column = 'member_ids',      type = 'jsonb' },
    }),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

themepark:add_table({
    name = 'public_transport_polygon',
    ids_type = 'area',
    geom = 'multipolygon',
    columns = themepark:columns('core/name', {
        { column = 'osm_type',        type = 'text', not_null = true },
        { column = 'osm_subtype',     type = 'text' },
        { column = 'public_transport', type = 'text', not_null = true },
        { column = 'layer',           type = 'int',  not_null = true },
        { column = 'ref',             type = 'text' },
        { column = 'operator',        type = 'text' },
        { column = 'network',         type = 'text' },
        { column = 'surface',         type = 'text' },
        { column = 'bus',             type = 'text' },
        { column = 'shelter',         type = 'text' },
        { column = 'bench',           type = 'text' },
        { column = 'lit',             type = 'text' },
        { column = 'wheelchair',      type = 'text' },
        { column = 'wheelchair_desc', type = 'text' },
        { column = 'member_ids',      type = 'jsonb' },
    }),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

-- ---------------------------------------------------------------------------

local function build_attrs(object)
    local t = get_osm_type_subtype(object)
    local a = {
        osm_type         = t.osm_type,
        osm_subtype      = t.osm_subtype,
        public_transport = object.tags.public_transport or 'other',
        layer            = theme.parse_layer_value(object.tags.layer),
        ref              = theme.get_ref(object.tags),
        operator         = object.tags.operator,
        network          = object.tags.network,
        surface          = object.tags.surface,
        bus              = object.tags.bus,
        shelter          = object.tags.shelter,
        bench            = object.tags.bench,
        lit              = object.tags.lit,
        wheelchair       = object.tags.wheelchair,
        wheelchair_desc  = theme.get_wheelchair_desc(object.tags),
    }
    theme.add_name(a, object)
    return a
end

themepark:add_proc('node', function(object, data)
    if not is_first_level_pt(object.tags) then return end
    local a = build_attrs(object)
    a.geom = object:as_point()
    themepark:insert('public_transport_point', a)
end)

themepark:add_proc('way', function(object, data)
    if not is_first_level_pt(object.tags) then return end
    local a = build_attrs(object)
    if object.tags.area == 'yes' or object.is_closed then
        a.geom = object:as_polygon()
        themepark:insert('public_transport_polygon', a)
    else
        a.geom = object:as_linestring()
        themepark:insert('public_transport_line', a)
    end
end)

themepark:add_proc('relation', function(object, data)
    if not is_first_level_pt(object.tags) then return end
    local a = build_attrs(object)
    a.member_ids = osm2pgsql.way_member_ids(object)
    if object.tags.type == 'multipolygon' then
        a.geom = object:as_multipolygon()
        themepark:insert('public_transport_polygon', a)
    else
        a.geom = object:as_multilinestring()
        themepark:insert('public_transport_line', a)
    end
end)

-- ---------------------------------------------------------------------------
