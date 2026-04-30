-- ---------------------------------------------------------------------------
--
-- Theme: pgosm
-- Topic: building_combined_point
--
-- Table: building_combined_point
-- All building geometries collapsed to a single point table.
--
-- ---------------------------------------------------------------------------

local themepark, theme, cfg = ...

-- ---------------------------------------------------------------------------

themepark:add_table({
    name = 'building_combined_point',
    ids_type = 'any',
    geom = 'point',
    columns = themepark:columns('core/name', {
        { column = 'osm_type',       type = 'text', not_null = true },
        { column = 'osm_subtype',    type = 'text' },
        { column = 'levels',         type = 'int' },
        { column = 'height',         sql_type = 'numeric' },
        { column = 'housenumber',    type = 'text' },
        { column = 'street',         type = 'text' },
        { column = 'city',           type = 'text' },
        { column = 'state',          type = 'text' },
        { column = 'postcode',       type = 'text' },
        { column = 'address',        type = 'text', not_null = true },
        { column = 'wheelchair',     type = 'text' },
        { column = 'wheelchair_desc', type = 'text' },
        { column = 'operator',       type = 'text' },
    }),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

-- ---------------------------------------------------------------------------

local function build_attrs(object)
    local osm_types = theme.get_osm_type_subtype_building(object)
    local a = {
        osm_type        = osm_types.osm_type,
        osm_subtype     = osm_types.osm_subtype,
        levels          = object.tags['building:levels'],
        height          = theme.parse_to_meters(object.tags['height']),
        housenumber     = object.tags['addr:housenumber'],
        street          = object.tags['addr:street'],
        city            = object.tags['addr:city'],
        state           = object.tags['addr:state'],
        postcode        = object.tags['addr:postcode'],
        address         = theme.get_address(object.tags),
        wheelchair      = object.tags.wheelchair,
        wheelchair_desc = theme.get_wheelchair_desc(object.tags),
        operator        = object.tags.operator,
    }
    theme.add_name(a, object)
    return a
end

themepark:add_proc('node', function(object, data)
    local address_only = theme.address_only_building(object.tags)
    if not theme.is_first_level_building(object.tags) and not address_only then return end
    local a = build_attrs(object)
    a.geom = object:as_point()
    themepark:insert('building_combined_point', a)
end)

themepark:add_proc('way', function(object, data)
    local address_only = theme.address_only_building(object.tags)
    if not theme.is_first_level_building(object.tags) and not address_only then return end
    if not object.is_closed then return end
    local a = build_attrs(object)
    a.geom = object:as_polygon():centroid()
    themepark:insert('building_combined_point', a)
end)

themepark:add_proc('relation', function(object, data)
    local address_only = theme.address_only_building(object.tags)
    if not theme.is_first_level_building(object.tags) and not address_only then return end
    if object.tags.type == 'multipolygon' or object.tags.type == 'boundary' then
        local a = build_attrs(object)
        a.geom = object:as_multipolygon():centroid()
        themepark:insert('building_combined_point', a)
    end
end)

-- ---------------------------------------------------------------------------
