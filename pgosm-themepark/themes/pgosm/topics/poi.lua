-- ---------------------------------------------------------------------------
--
-- Theme: pgosm
-- Topic: poi
--
-- Tables: poi_point, poi_line, poi_polygon
--
-- ---------------------------------------------------------------------------

local themepark, theme, cfg = ...

local poi_cols = {
    { column = 'osm_type',    type = 'text', not_null = true },
    { column = 'osm_subtype', type = 'text', not_null = true },
    { column = 'housenumber', type = 'text' },
    { column = 'street',      type = 'text' },
    { column = 'city',        type = 'text' },
    { column = 'state',       type = 'text' },
    { column = 'postcode',    type = 'text' },
    { column = 'address',     type = 'text', not_null = true },
    { column = 'operator',    type = 'text' },
}

-- ---------------------------------------------------------------------------

themepark:add_table({
    name = 'poi_point',
    ids_type = 'node',
    geom = 'point',
    columns = themepark:columns('core/name', poi_cols),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

themepark:add_table({
    name = 'poi_line',
    ids_type = 'way',
    geom = 'linestring',
    columns = themepark:columns('core/name', poi_cols),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

themepark:add_table({
    name = 'poi_polygon',
    ids_type = 'way',
    geom = 'multipolygon',
    columns = themepark:columns('core/name', {
        { column = 'osm_type',    type = 'text', not_null = true },
        { column = 'osm_subtype', type = 'text', not_null = true },
        { column = 'housenumber', type = 'text' },
        { column = 'street',      type = 'text' },
        { column = 'city',        type = 'text' },
        { column = 'state',       type = 'text' },
        { column = 'postcode',    type = 'text' },
        { column = 'address',     type = 'text', not_null = true },
        { column = 'operator',    type = 'text' },
        { column = 'member_ids',  type = 'jsonb' },
    }),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

-- ---------------------------------------------------------------------------

local function build_attrs(object)
    local osm_types = theme.get_osm_type_subtype_poi(object)
    local a = {
        osm_type    = osm_types.osm_type,
        osm_subtype = osm_types.osm_subtype,
        housenumber = object.tags['addr:housenumber'],
        street      = object.tags['addr:street'],
        city        = object.tags['addr:city'],
        state       = object.tags['addr:state'],
        postcode    = object.tags['addr:postcode'],
        address     = theme.get_address(object.tags),
        operator    = object:grab_tag('operator'),
    }
    theme.add_name(a, object)
    return a
end

themepark:add_proc('node', function(object, data)
    if not theme.is_first_level_poi(object.tags) then return end
    if not theme.second_level_tag_check_poi(object) then return end
    local a = build_attrs(object)
    a.geom = object:as_point()
    themepark:insert('poi_point', a)
end)

themepark:add_proc('way', function(object, data)
    if not theme.is_first_level_poi(object.tags) then return end
    if not theme.second_level_tag_check_poi(object) then return end
    local a = build_attrs(object)
    if object.is_closed then
        a.geom = object:as_polygon()
        themepark:insert('poi_polygon', a)
    else
        a.geom = object:as_multilinestring()
        themepark:insert('poi_line', a)
    end
end)

themepark:add_proc('relation', function(object, data)
    if not theme.is_first_level_poi(object.tags) then return end
    if not theme.second_level_tag_check_poi(object) then return end
    if object.tags.type == 'multipolygon' or object.tags.type == 'boundary' then
        local a = build_attrs(object)
        a.member_ids = osm2pgsql.way_member_ids(object)
        a.geom = object:as_multipolygon()
        themepark:insert('poi_polygon', a)
    end
end)

-- ---------------------------------------------------------------------------
