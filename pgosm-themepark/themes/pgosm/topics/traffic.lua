-- ---------------------------------------------------------------------------
--
-- Theme: pgosm
-- Topic: traffic
--
-- Tables: traffic_point, traffic_line, traffic_polygon
--
-- ---------------------------------------------------------------------------

local themepark, theme, cfg = ...

-- ---------------------------------------------------------------------------

themepark:add_table({
    name = 'traffic_point',
    ids_type = 'node',
    geom = 'point',
    columns = {
        { column = 'osm_type',    type = 'text', not_null = true },
        { column = 'osm_subtype', type = 'text' },
    },
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

themepark:add_table({
    name = 'traffic_line',
    ids_type = 'way',
    geom = 'linestring',
    columns = {
        { column = 'osm_type',    type = 'text', not_null = true },
        { column = 'osm_subtype', type = 'text' },
    },
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

themepark:add_table({
    name = 'traffic_polygon',
    ids_type = 'way',
    geom = 'multipolygon',
    columns = {
        { column = 'osm_type',    type = 'text', not_null = true },
        { column = 'osm_subtype', type = 'text' },
    },
    indexes = {
        { column = 'geom',     method = 'gist' },
        { column = 'osm_type', method = 'btree' },
    },
})

-- ---------------------------------------------------------------------------

local highway_traffic_values = {
    'traffic_signals', 'mini_roundabout', 'stop', 'crossing', 'speed_camera',
    'motorway_junction', 'turning_circle', 'ford', 'street_lamp', 'services'
}
local is_highway_traffic = theme.make_check_in_list_func(highway_traffic_values)

local amenity_traffic_values = { 'fuel', 'parking', 'bicycle_parking' }
local is_amenity_traffic = theme.make_check_in_list_func(amenity_traffic_values)

local function has_traffic_tags(tags)
    return tags.highway or tags.railway or tags.barrier
        or tags.traffic_calming or tags.amenity or tags.noexit
end

local function classify_node(object)
    local tags = object.tags
    if tags.highway and is_highway_traffic(tags.highway) then
        return object:grab_tag('highway'), nil
    elseif tags.railway == 'level_crossing' then
        return 'crossing', nil
    elseif tags.barrier then
        return 'barrier', object:grab_tag('barrier')
    elseif tags.traffic_calming then
        return 'traffic_calming', object:grab_tag('traffic_calming')
    elseif tags.amenity and is_amenity_traffic(tags.amenity) then
        return 'amenity', object:grab_tag('amenity')
    elseif tags.noexit then
        return 'noexit', nil
    end
    return nil, nil
end

-- ---------------------------------------------------------------------------

themepark:add_proc('node', function(object, data)
    if not has_traffic_tags(object.tags) then return end
    local osm_type, osm_subtype = classify_node(object)
    if not osm_type then return end
    themepark:insert('traffic_point', {
        osm_type    = osm_type,
        osm_subtype = osm_subtype,
        geom        = object:as_point(),
    })
end)

themepark:add_proc('way', function(object, data)
    if not has_traffic_tags(object.tags) then return end
    local tags = object.tags
    local osm_type, osm_subtype

    if tags.highway and is_highway_traffic(tags.highway) then
        osm_type = object:grab_tag('highway')
    elseif tags.railway == 'level_crossing' then
        osm_type = 'crossing'
    elseif tags.barrier then
        osm_type = 'barrier'; osm_subtype = object:grab_tag('barrier')
    elseif tags.traffic_calming then
        osm_type = 'traffic_calming'; osm_subtype = object:grab_tag('traffic_calming')
    elseif tags.amenity and is_amenity_traffic(tags.amenity) then
        osm_type = 'amenity'; osm_subtype = object:grab_tag('amenity')
    elseif tags.noexit then
        if object.is_closed then return end  -- noexit doesn't make sense for polygons
        osm_type = 'noexit'
    else
        return
    end

    if object.is_closed then
        themepark:insert('traffic_polygon', {
            osm_type    = osm_type,
            osm_subtype = osm_subtype,
            geom        = object:as_polygon(),
        })
    else
        themepark:insert('traffic_line', {
            osm_type    = osm_type,
            osm_subtype = osm_subtype,
            geom        = object:as_linestring(),
        })
    end
end)

-- ---------------------------------------------------------------------------
