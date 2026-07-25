-- Restricted area 1:
-- Airspace boundary. Usually military or political, with no physical terrain obstacles.

-- Antimeridian:
-- qWrap = :west_lon > :east_lon
-- rWrap = min_lonx > max_lonx
-- | qWrap | rWrap | overlap condition                                                                            |
-- |-------|-------|----------------------------------------------------------------------------------------------|
-- | no    | no    | min_lonx < :east_lon AND max_lonx > :west_lon                                                |
-- | yes   | no    | row overlaps either [west,180] or [-180,east] → max_lonx > :west_lon OR min_lonx < :east_lon |
-- | no    | yes   | query overlaps either row piece → :east_lon > min_lonx OR :west_lon < max_lonx               |
-- | yes   | yes   | both wrap → they always share the 180 line → TRUE                                            |

select
    type,
    name,
    geometry
from boundary
where
    min_laty < :north_lat and max_laty > :south_lat and
    case
        -- neither box crosses 180
        when :west_lon <= :east_lon and min_lonx <= max_lonx then
            (min_lonx < :east_lon and max_lonx > :west_lon)
        -- only the query box crosses 180
        when :west_lon > :east_lon and min_lonx <= max_lonx then
            (max_lonx > :west_lon or min_lonx < :east_lon)
        -- only the row box crosses 180
        when :west_lon <= :east_lon and min_lonx > max_lonx then
            (:east_lon > min_lonx or :west_lon < max_lonx)
        -- both cross 180: they necessarily share the antimeridian
        else true
    end
    and type in  -- Usage: main.py "Restricted area" section.
   ('P',  -- Prohibited Area: Flights are strictly forbidden for national security reasons (e.g., over the White House).
    'R',  -- Restricted Area: Flights are forbidden when the area is "active" because of invisible hazards like artillery firing or missile testing.
    'M',  -- Military Operations Area: Airspace where high-speed military training happens. Civilian planes can fly through, but it is highly discouraged.
    'W',  -- Warning Area: Airspace containing activity that may be hazardous to nonparticipating aircraft, located out over the ocean in international waters.
    'AL',  -- Alert Area: High volumes of unusual civilian activity, such as intense flight school training.
    'DA',  -- Danger Area: The international equivalent of a Restricted or Warning area. Activities dangerous to flight take place here.
    'CN',  -- Caution Area: Airspace where unique hazards exist, requiring extra pilot vigilance.
    'TR',  -- Training Area: A designated zone specifically mapped for flight training maneuvers.
    'U'  -- Unidentified: Used in the database when a restrictive airspace exists but the specific category is unpublished or unknown.
   )
