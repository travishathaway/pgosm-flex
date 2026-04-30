-- ---------------------------------------------------------------------------
--
-- Theme: pgosm
-- Topic: poi_combined_point
--
-- Table: poi_combined_point
-- All POI geometries collapsed to a single point table.
--
-- ---------------------------------------------------------------------------

local themepark, theme, cfg = ...

-- ---------------------------------------------------------------------------

themepark:add_table({
    name = 'poi_combined_point',
    ids_type = 'any',
    geom = 'point',
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
    themepark:insert('poi_combined_point', a)
end)

themepark:add_proc('way', function(object, data)
    if not theme.is_first_level_poi(object.tags) then return end
    if not theme.second_level_tag_check_poi(object) then return end
    local a = build_attrs(object)
    if object.is_closed then
        a.geom = object:as_polygon():centroid()
    else
        a.geom = object:as_linestring():centroid()
    end
    themepark:insert('poi_combined_point', a)
end)

themepark:add_proc('relation', function(object, data)
    if not theme.is_first_level_poi(object.tags) then return end
    if not theme.second_level_tag_check_poi(object) then return end
    if object.tags.type == 'multipolygon' or object.tags.type == 'boundary' then
        local a = build_attrs(object)
        a.geom = object:as_multipolygon():centroid()
        themepark:insert('poi_combined_point', a)
    end
end)

-- ---------------------------------------------------------------------------
