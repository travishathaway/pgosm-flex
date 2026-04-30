-- ---------------------------------------------------------------------------
--
-- Theme: pgosm
-- Topic: unitable
--
-- Table: unitable
-- All OSM objects with any geometry in a single wide table.
-- Intended for data exploration only, NOT for production use.
--
-- ---------------------------------------------------------------------------

local themepark, theme, cfg = ...

-- ---------------------------------------------------------------------------

themepark:add_table({
    name = 'unitable',
    ids_type = 'any',
    geom = 'geometry',
    columns = {
        { column = 'tags', type = 'jsonb' },
    },
    indexes = {
        { column = 'geom', method = 'gist' },
    },
})

-- ---------------------------------------------------------------------------

local function clean_tags(tags)
    tags.odbl = nil
    tags.created_by = nil
    tags.source = nil
    tags['source:ref'] = nil
    return next(tags) == nil
end

themepark:add_proc('node', function(object, data)
    if clean_tags(object.tags) then return end
    themepark:insert('unitable', { tags = object.tags, geom = object:as_point() })
end)

themepark:add_proc('way', function(object, data)
    if clean_tags(object.tags) then return end
    themepark:insert('unitable', { tags = object.tags, geom = object:as_linestring() })
end)

themepark:add_proc('relation', function(object, data)
    if clean_tags(object.tags) then return end
    local t = object.tags.type
    if t == 'multipolygon' or t == 'boundary' then
        themepark:insert('unitable', { tags = object.tags, geom = object:as_multipolygon() })
    elseif t == 'route' or t == 'route_master' or t == 'public_transport'
            or t == 'waterway' or t == 'network' or t == 'building'
            or t == 'street' or t == 'bridge' or t == 'tunnel' then
        themepark:insert('unitable', { tags = object.tags, geom = object:as_multilinestring() })
    end
end)

-- ---------------------------------------------------------------------------
