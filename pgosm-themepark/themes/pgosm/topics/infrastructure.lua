-- ---------------------------------------------------------------------------
--
-- Theme: pgosm
-- Topic: infrastructure
--
-- Tables: infrastructure_point, infrastructure_line, infrastructure_polygon
--
-- ---------------------------------------------------------------------------

local themepark, theme, cfg = ...

local infrastructure_keys = { 'aeroway', 'amenity', 'emergency', 'highway', 'man_made', 'power', 'utility' }
local is_infrastructure = theme.make_check_in_list_func(infrastructure_keys)

local function get_osm_type_subtype(tags)
    local t = {}
    if tags.amenity == 'fire_hydrant' or tags.emergency == 'fire_hydrant' then
        t.osm_type = 'emergency'; t.osm_subtype = 'fire_hydrant'
    elseif tags.amenity == 'emergency_phone' or tags.emergency == 'phone' then
        t.osm_type = 'emergency'; t.osm_subtype = 'phone'
    elseif tags.emergency then
        t.osm_type = 'emergency'; t.osm_subtype = tags.emergency
    elseif tags.highway == 'emergency_access_point' then
        t.osm_type = 'emergency'; t.osm_subtype = 'highway_access'
    elseif tags.man_made == 'tower' or tags.man_made == 'communications_tower'
            or tags.man_made == 'mast' or tags.man_made == 'lighthouse'
            or tags.man_made == 'flagpole' then
        t.osm_type = tags.man_made; t.osm_subtype = tags['tower:type']
    elseif tags.man_made == 'silo' or tags.man_made == 'storage_tank'
            or tags.man_made == 'water_tower' or tags.man_made == 'reservoir_covered' then
        t.osm_type = tags.man_made; t.osm_subtype = tags['content']
    elseif tags.power then
        t.osm_type = 'power'; t.osm_subtype = tags.power
    elseif tags.utility then
        t.osm_type = 'utility'; t.osm_subtype = nil
    elseif tags.aeroway then
        t.osm_type = 'aeroway'; t.osm_subtype = tags.aeroway
    else
        t.osm_type = 'unknown'; t.osm_subtype = nil
    end
    -- Filter out "emergency=no"
    if t.osm_type == 'emergency' and t.osm_subtype == 'no' then
        t.osm_type = 'unknown'; t.osm_subtype = nil
    end
    return t
end

local infra_cols = {
    { column = 'osm_type',    type = 'text', not_null = true },
    { column = 'osm_subtype', type = 'text' },
    { column = 'ele',         type = 'int' },
    { column = 'height',      sql_type = 'numeric' },
    { column = 'operator',    type = 'text' },
    { column = 'material',    type = 'text' },
}

-- ---------------------------------------------------------------------------

themepark:add_table({
    name = 'infrastructure_point',
    ids_type = 'node',
    geom = 'point',
    columns = themepark:columns('core/name', infra_cols),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

themepark:add_table({
    name = 'infrastructure_line',
    ids_type = 'way',
    geom = 'linestring',
    columns = themepark:columns('core/name', infra_cols),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

themepark:add_table({
    name = 'infrastructure_polygon',
    ids_type = 'way',
    geom = 'multipolygon',
    columns = themepark:columns('core/name', infra_cols),
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

-- ---------------------------------------------------------------------------

local function build_attrs(object)
    local t = get_osm_type_subtype(object.tags)
    if t.osm_type == 'unknown' then return nil end
    local a = {
        osm_type    = t.osm_type,
        osm_subtype = t.osm_subtype,
        ele         = theme.parse_to_meters(object.tags.ele),
        height      = theme.parse_to_meters(object.tags['height']),
        operator    = object.tags.operator,
        material    = object.tags.material,
    }
    theme.add_name(a, object)
    return a
end

themepark:add_proc('node', function(object, data)
    if not is_infrastructure(object.tags) then return end
    local a = build_attrs(object)
    if not a then return end
    a.geom = object:as_point()
    themepark:insert('infrastructure_point', a)
end)

themepark:add_proc('way', function(object, data)
    if not is_infrastructure(object.tags) then return end
    local a = build_attrs(object)
    if not a then return end
    if object.is_closed then
        a.geom = object:as_polygon()
        themepark:insert('infrastructure_polygon', a)
    else
        a.geom = object:as_linestring()
        themepark:insert('infrastructure_line', a)
    end
end)

-- ---------------------------------------------------------------------------
