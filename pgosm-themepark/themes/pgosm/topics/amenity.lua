-- ---------------------------------------------------------------------------
--
-- Theme: pgosm
-- Topic: amenity
--
-- Tables: amenity_point, amenity_line, amenity_polygon
--
-- ---------------------------------------------------------------------------

local themepark, theme, cfg = ...

local amenity_first_level_keys = { 'amenity', 'bench', 'brewery' }
local is_first_level_amenity = theme.make_check_in_list_func(amenity_first_level_keys)

local function get_osm_type_subtype(object)
    local amenity = object.tags.amenity
    local osm_type, osm_subtype

    if amenity == nil and object.tags.bench == 'yes' then
        osm_type = 'bench'
    elseif amenity == nil and object.tags.brewery then
        osm_type = 'brewery'
    elseif amenity == 'restaurant' or amenity == 'fast_food' or amenity == 'cafe' then
        osm_type = amenity; osm_subtype = object.tags.cuisine
    elseif amenity == 'shelter' then
        osm_type = amenity; osm_subtype = object.tags.shelter_type
    elseif amenity ~= nil then
        osm_type = amenity
    end

    return osm_type, osm_subtype
end

local address_cols = {
    { column = 'osm_type',       type = 'text', not_null = true },
    { column = 'osm_subtype',    type = 'text' },
    { column = 'housenumber',    type = 'text' },
    { column = 'street',         type = 'text' },
    { column = 'city',           type = 'text' },
    { column = 'state',          type = 'text' },
    { column = 'postcode',       type = 'text' },
    { column = 'address',        type = 'text', not_null = true },
    { column = 'wheelchair',     type = 'text' },
    { column = 'wheelchair_desc', type = 'text' },
}

-- ---------------------------------------------------------------------------

themepark:add_table({
    name = 'amenity_point',
    ids_type = 'node',
    geom = 'point',
    columns = themepark:columns('core/name', address_cols),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

themepark:add_table({
    name = 'amenity_line',
    ids_type = 'way',
    geom = 'linestring',
    columns = themepark:columns('core/name', address_cols),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

themepark:add_table({
    name = 'amenity_polygon',
    ids_type = 'area',
    geom = 'multipolygon',
    columns = themepark:columns('core/name', address_cols),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

-- ---------------------------------------------------------------------------

local function build_attrs(object)
    local osm_type, osm_subtype = get_osm_type_subtype(object)
    if osm_type == nil then return nil end
    local a = {
        osm_type       = osm_type,
        osm_subtype    = osm_subtype,
        housenumber    = object.tags['addr:housenumber'],
        street         = object.tags['addr:street'],
        city           = object.tags['addr:city'],
        state          = object.tags['addr:state'],
        postcode       = object.tags['addr:postcode'],
        address        = theme.get_address(object.tags),
        wheelchair     = object.tags.wheelchair,
        wheelchair_desc = theme.get_wheelchair_desc(object.tags),
    }
    theme.add_name(a, object)
    return a
end

themepark:add_proc('node', function(object, data)
    if not is_first_level_amenity(object.tags) then return end
    local a = build_attrs(object)
    if not a then return end
    a.geom = object:as_point()
    themepark:insert('amenity_point', a)
end)

themepark:add_proc('way', function(object, data)
    if not is_first_level_amenity(object.tags) then return end
    local a = build_attrs(object)
    if not a then return end
    if object.is_closed then
        a.geom = object:as_polygon()
        themepark:insert('amenity_polygon', a)
    else
        a.geom = object:as_linestring()
        themepark:insert('amenity_line', a)
    end
end)

themepark:add_proc('relation', function(object, data)
    if not is_first_level_amenity(object.tags) then return end
    local a = build_attrs(object)
    if not a then return end
    a.geom = object:as_multipolygon()
    themepark:insert('amenity_polygon', a)
end)

-- ---------------------------------------------------------------------------
