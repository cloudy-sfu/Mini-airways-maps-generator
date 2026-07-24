select
    r.lonx,
    r.laty,
    r.heading,
    r.length * 0.0003048 as length_km, -- feet to km
    re2.name as sec_ident,
    re1.is_takeoff as pri_takeoff,
    re1.is_landing as pri_land,
    re2.is_takeoff as sec_takeoff,
    re2.is_landing as sec_land
from runway r
    join runway_end re1 on r.primary_end_id = re1.runway_end_id
    join runway_end re2 on r.secondary_end_id = re2.runway_end_id
where r.airport_id = :airport_id