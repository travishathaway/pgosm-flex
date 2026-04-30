-- ---------------------------------------------------------------------------
--
-- Theme: pgosm
--
-- Shared helper functions for all pgosm topics.
-- Functions are exposed on the theme table so topics can access them via
-- theme.<func>(). No global variables are set here.
--
-- ---------------------------------------------------------------------------

local theme = {}

-- ---------------------------------------------------------------------------
-- Numeric / unit parsing helpers
-- ---------------------------------------------------------------------------

-- Parse a tag value like "1800", "1955 m" or "8001 ft" and return a number in meters
function theme.parse_to_meters(input)
    if not input then return nil end
    local num1 = tonumber(input)
    if num1 then return num1 end
    if input:sub(-1) == 'm' then
        local num2 = tonumber(input:sub(1, -2))
        if num2 then return num2 end
    end
    if input:sub(-2) == 'ft' then
        local num3 = tonumber(input:sub(1, -3))
        if num3 then return num3 * 0.3048 end
    end
    return nil
end


-- Parse a maxspeed value like "30" or "55 mph" and return a number in km/h
function theme.parse_speed(input)
    if not input then return nil end
    local maxspeed = tonumber(input)
    if maxspeed then return maxspeed end
    if input:sub(-3) == 'mph' then
        local num = tonumber(input:sub(1, -4))
        if num then return math.floor(num * 1.60934) end
    end
    return nil
end


function theme.parse_layer_value(input)
    if not input then return 0 end
    local layer = tonumber(input)
    if layer then return layer end
    return 0
end


function theme.parse_admin_level(input)
    if not input then return nil end
    local admin_level = tonumber(input)
    if admin_level then return admin_level end
    return nil
end


-- ---------------------------------------------------------------------------
-- String helpers
-- ---------------------------------------------------------------------------

function theme.starts_with(str, start)
    return str:sub(1, #start) == start
end

function theme.ends_with(str, ending)
    return ending == "" or str:sub(-#ending) == ending
end


-- ---------------------------------------------------------------------------
-- Road / routing helpers
-- ---------------------------------------------------------------------------

function theme.major_road(highway)
    return (highway == 'motorway'
        or highway == 'motorway_link'
        or highway == 'primary'
        or highway == 'primary_link'
        or highway == 'secondary'
        or highway == 'secondary_link'
        or highway == 'tertiary'
        or highway == 'tertiary_link'
        or highway == 'trunk'
        or highway == 'trunk_link')
end


function theme.routable_foot(tags)
    if (tags.access == 'no' or tags.access == 'private'
            or tags.foot == 'no' or tags.foot == 'private') then
        return false
    elseif (tags.highway == 'footway' or tags.footway
            or tags.foot == 'yes' or tags.foot == 'permissive'
            or tags.foot == 'designated' or tags.highway == 'pedestrian'
            or tags.highway == 'crossing' or tags.highway == 'platform'
            or tags.highway == 'social_path' or tags.highway == 'steps'
            or tags.highway == 'trailhead' or tags.highway == 'track'
            or tags.highway == 'path' or tags.highway == 'unclassified'
            or tags.highway == 'service' or tags.highway == 'residential'
            or tags.highway == 'living_street' or tags.highway == 'elevator'
            or tags.highway == 'corridor' or tags.highway == 'foot') then
        return true
    end
    return false
end


function theme.routable_cycle(tags)
    if (tags.access == 'no' or tags.access == 'private'
            or tags.bicycle == 'no' or tags.bicycle == 'private') then
        return false
    elseif (tags.cycleway or tags.bicycle == 'yes'
            or tags.bicycle == 'designated' or tags.bicycle == 'permissive'
            or tags.highway == 'cycleway' or tags.highway == 'track'
            or tags.highway == 'path' or tags.highway == 'unclassified'
            or tags.highway == 'service' or tags.highway == 'residential'
            or tags.highway == 'tertiary' or tags.highway == 'tertiary_link'
            or tags.highway == 'secondary' or tags.highway == 'secondary_link'
            or tags.highway == 'living_street') then
        return true
    end
    return false
end


function theme.routable_motor(tags)
    if (tags.access == 'no' or tags.access == 'private'
            or tags.motor_vehicle == 'no' or tags.motor_vehicle == 'private') then
        return false
    elseif (tags.highway == 'motorway' or tags.highway == 'motorway_link'
            or tags.highway == 'trunk' or tags.highway == 'trunk_link'
            or tags.highway == 'primary' or tags.highway == 'primary_link'
            or tags.highway == 'secondary' or tags.highway == 'secondary_link'
            or tags.highway == 'tertiary' or tags.highway == 'tertiary_link'
            or tags.highway == 'residential' or tags.highway == 'service'
            or tags.highway == 'unclassified' or tags.highway == 'living_street'
            or tags.highway == 'rest_area' or tags.highway == 'raceway'
            or tags.motor_vehicle == 'yes' or tags.motor_vehicle == 'permissive') then
        return true
    end
    return false
end


-- ---------------------------------------------------------------------------
-- Ref / address helpers
-- ---------------------------------------------------------------------------

function theme.get_ref(tags)
    if tags.local_ref then return tags.local_ref
    elseif tags.route_ref then return tags.route_ref
    elseif tags.nat_ref then return tags.nat_ref
    elseif tags.ref then return tags.ref
    elseif tags.alt_ref then return tags.alt_ref
    elseif tags.old_ref then return tags.old_ref
    end
    return nil
end


function theme.get_address(tags)
    local housenumber = tags['addr:housenumber']
    local street      = tags['addr:street']
    local city        = tags['addr:city']
    local state       = tags['addr:state']
    local postcode    = tags['addr:postcode']

    local housenumber_street = ''
    if housenumber ~= nil and street ~= nil then
        housenumber_street = housenumber .. ' ' .. street
    elseif housenumber == nil and street == nil then
        housenumber_street = ''
    elseif housenumber == nil then
        housenumber_street = street
    else
        housenumber_street = housenumber
    end

    city     = city     or ''
    state    = state    or ''
    postcode = postcode or ''

    local all_but_state_postcode = (housenumber_street ~= '' and city ~= '')
        and (housenumber_street .. ', ' .. city)
        or  (housenumber_street .. city)

    local all_but_postcode = (all_but_state_postcode ~= '' and state ~= '')
        and (all_but_state_postcode .. ', ' .. state)
        or  (all_but_state_postcode .. state)

    local address = (all_but_postcode ~= '' and postcode ~= '')
        and (all_but_postcode .. ', ' .. postcode)
        or  (all_but_postcode .. postcode)

    return address
end


function theme.get_wheelchair_desc(tags)
    return tags['wheelchair:description']
end


-- ---------------------------------------------------------------------------
-- make_check_in_list_func: returns a function that checks if any tag key
-- in the given list exists in a tags table.
-- ---------------------------------------------------------------------------

function theme.make_check_in_list_func(list)
    local h = {}
    for _, k in ipairs(list) do h[k] = true end
    return function(tags)
        for k, _ in pairs(tags) do
            if h[k] then return true end
        end
        return false
    end
end


-- ---------------------------------------------------------------------------
-- Building helpers
-- ---------------------------------------------------------------------------

local building_first_level_keys = { 'building', 'building:part', 'office', 'door', 'entrance' }
theme.is_first_level_building = theme.make_check_in_list_func(building_first_level_keys)


function theme.address_only_building(tags)
    if tags.shop or tags.amenity or tags.building or tags['building:part']
            or tags.landuse or tags.leisure or tags.office or tags.tourism
            or tags.boundary or tags.natural or tags.aeroway or tags.demolished then
        return false
    end
    for k, _ in pairs(tags) do
        if k ~= nil and theme.starts_with(k, "addr:") then
            return true
        end
    end
    return false
end


function theme.get_osm_type_subtype_building(object)
    local t = {}
    local address_only = theme.address_only_building(object.tags)
    if object.tags.building then
        t.osm_type = 'building'; t.osm_subtype = object.tags.building
    elseif object.tags['building:part'] then
        t.osm_type = 'building_part'; t.osm_subtype = object.tags['building:part']
    elseif object.tags.office then
        t.osm_type = 'office'; t.osm_subtype = object.tags.office
    elseif address_only then
        t.osm_type = 'address'; t.osm_subtype = nil
    elseif object.tags.entrance then
        t.osm_type = 'entrance'; t.osm_subtype = object.tags.entrance
    elseif object.tags.door then
        t.osm_type = 'door'; t.osm_subtype = object.tags.door
    else
        t.osm_type = 'unknown'; t.osm_subtype = nil
    end
    return t
end


-- ---------------------------------------------------------------------------
-- POI helpers
-- ---------------------------------------------------------------------------

local poi_first_level_keys = {
    'building', 'shop', 'amenity', 'leisure',
    'man_made', 'tourism', 'landuse', 'natural', 'historic'
}
theme.is_first_level_poi = theme.make_check_in_list_func(poi_first_level_keys)


local function building_poi(object)
    -- Requires add_name to already have been called or a name check
    return (object.tags.name and object.tags.name ~= '') or object.tags.operator
end

local function landuse_poi(object)
    local v = object.tags.landuse
    return v == 'cemetery' or v == 'orchard' or v == 'railway'
        or v == 'village_green' or v == 'vineyard'
end

local function man_made_poi(object)
    local v = object.tags.man_made
    return v == 'beacon' or v == 'chimney' or v == 'communications_tower'
        or v == 'crane' or v == 'flagpole' or v == 'lighthouse' or v == 'mast'
        or v == 'obelisk' or v == 'observatory' or v == 'offshore_platform'
        or v == 'pier' or v == 'silo' or v == 'survey_point' or v == 'telescope'
        or v == 'tower' or v == 'water_tap' or v == 'water_tower'
        or v == 'water_well' or v == 'windmill' or v == 'works'
end

local function natural_poi(object)
    local v = object.tags.natural
    return v == 'peak' or v == 'glacier' or v == 'reef'
        or v == 'hot_spring' or v == 'bay'
end


function theme.second_level_tag_check_poi(object)
    if object.tags.natural  and not natural_poi(object)  then return false end
    if object.tags.landuse  and not landuse_poi(object)  then return false end
    if object.tags.building and not building_poi(object) then return false end
    if object.tags.man_made and not man_made_poi(object) then return false end
    return true
end


function theme.get_osm_type_subtype_poi(object)
    local t = {}
    if object.tags.shop then
        t.osm_type = 'shop';     t.osm_subtype = object:grab_tag('shop')
    elseif object.tags.amenity then
        t.osm_type = 'amenity';  t.osm_subtype = object:grab_tag('amenity')
    elseif object.tags.building then
        t.osm_type = 'building'; t.osm_subtype = object:grab_tag('building')
    elseif object.tags.leisure then
        t.osm_type = 'leisure';  t.osm_subtype = object:grab_tag('leisure')
    elseif object.tags.landuse then
        t.osm_type = 'landuse';  t.osm_subtype = object:grab_tag('landuse')
    elseif object.tags.natural then
        t.osm_type = 'natural';  t.osm_subtype = object:grab_tag('natural')
    elseif object.tags.man_made then
        t.osm_type = 'man_made'; t.osm_subtype = object:grab_tag('man_made')
    elseif object.tags.tourism then
        t.osm_type = 'tourism';  t.osm_subtype = object:grab_tag('tourism')
    elseif object.tags.historic then
        t.osm_type = 'historic'; t.osm_subtype = object.tags['historic']
    else
        t.osm_type = 'Unknown';  t.osm_subtype = 'Unknown'
    end
    return t
end


-- ---------------------------------------------------------------------------
-- Shop helpers
-- ---------------------------------------------------------------------------

local shop_first_level_keys = { 'shop', 'amenity' }
theme.is_first_level_shop = theme.make_check_in_list_func(shop_first_level_keys)


function theme.get_osm_type_subtype_shop(object)
    local t = {}
    if object.tags.shop then
        t.osm_type = 'shop'; t.osm_subtype = object:grab_tag('shop')
    elseif object.tags.amenity == 'vending_machine'
            or object.tags.amenity == 'car_rental'
            or object.tags.amenity == 'motorcycle_rental'
            or object.tags.amenity == 'cafe'
            or object.tags.amenity == 'phone_repair'
            or object.tags.amenity == 'music_school'
            or object.tags.amenity == 'pub'
            or object.tags.amenity == 'pharmacy'
            or object.tags.amenity == 'ticket_booth'
            or object.tags.amenity == 'shop' then
        t.osm_type = 'amenity'; t.osm_subtype = object:grab_tag('amenity')
    end
    return t
end


-- ---------------------------------------------------------------------------

return theme

-- ---------------------------------------------------------------------------
