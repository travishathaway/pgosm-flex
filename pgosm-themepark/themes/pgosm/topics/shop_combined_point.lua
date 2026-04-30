-- ---------------------------------------------------------------------------
--
-- Theme: pgosm
-- Topic: shop_combined_point
--
-- Table: shop_combined_point
-- All shop geometries collapsed to a single point table.
--
-- ---------------------------------------------------------------------------

local themepark, theme, cfg = ...

-- ---------------------------------------------------------------------------

themepark:add_table({
    name = 'shop_combined_point',
    ids_type = 'any',
    geom = 'point',
    columns = themepark:columns('core/name', {
        { column = 'osm_type',       type = 'text', not_null = true },
        { column = 'osm_subtype',    type = 'text', not_null = true },
        { column = 'housenumber',    type = 'text' },
        { column = 'street',         type = 'text' },
        { column = 'city',           type = 'text' },
        { column = 'state',          type = 'text' },
        { column = 'postcode',       type = 'text' },
        { column = 'address',        type = 'text', not_null = true },
        { column = 'phone',          type = 'text' },
        { column = 'wheelchair',     type = 'text' },
        { column = 'wheelchair_desc', type = 'text' },
        { column = 'operator',       type = 'text' },
        { column = 'brand',          type = 'text' },
        { column = 'website',        type = 'text' },
    }),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

-- ---------------------------------------------------------------------------

local function build_attrs(object)
    local osm_types = theme.get_osm_type_subtype_shop(object)
    local a = {
        osm_type        = osm_types.osm_type,
        osm_subtype     = osm_types.osm_subtype,
        housenumber     = object.tags['addr:housenumber'],
        street          = object.tags['addr:street'],
        city            = object.tags['addr:city'],
        state           = object.tags['addr:state'],
        postcode        = object.tags['addr:postcode'],
        address         = theme.get_address(object.tags),
        phone           = object:grab_tag('phone'),
        wheelchair      = object.tags.wheelchair,
        wheelchair_desc = theme.get_wheelchair_desc(object.tags),
        operator        = object:grab_tag('operator'),
        brand           = object:grab_tag('brand'),
        website         = object:grab_tag('website'),
    }
    theme.add_name(a, object)
    return a
end

themepark:add_proc('node', function(object, data)
    if not theme.is_first_level_shop(object.tags) then return end
    local a = build_attrs(object)
    a.geom = object:as_point()
    themepark:insert('shop_combined_point', a)
end)

themepark:add_proc('way', function(object, data)
    if not theme.is_first_level_shop(object.tags) then return end
    if not object.is_closed then return end
    local a = build_attrs(object)
    a.geom = object:as_polygon():centroid()
    themepark:insert('shop_combined_point', a)
end)

-- ---------------------------------------------------------------------------
