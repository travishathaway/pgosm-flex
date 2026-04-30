-- ---------------------------------------------------------------------------
--
-- Theme: pgosm
-- Topic: tags
--
-- Table: tags
-- All OSM tag data in a single table without geometry.
--
-- ---------------------------------------------------------------------------

local themepark, theme, cfg = ...

-- ---------------------------------------------------------------------------

themepark:add_table({
    name = 'tags',
    ids_type = 'any',
    columns = {
        { column = 'tags', type = 'jsonb' },
    },
    indexes = {},
})

-- ---------------------------------------------------------------------------

local function clean_tags(tags)
    tags.odbl = nil
    tags.created_by = nil
    tags.source = nil
    tags['source:ref'] = nil
    return next(tags) == nil
end

local function process(object, table_name)
    if clean_tags(object.tags) then return end
    themepark:insert(table_name, { tags = object.tags })
end

themepark:add_proc('node',     function(object, data) process(object, 'tags') end)
themepark:add_proc('way',      function(object, data) process(object, 'tags') end)
themepark:add_proc('relation', function(object, data) process(object, 'tags') end)

-- ---------------------------------------------------------------------------
