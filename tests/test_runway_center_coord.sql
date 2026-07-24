select r.primary_lonx
     , r.secondary_lonx
     , r.lonx
     , r.primary_laty
     , r.secondary_laty
     , r.laty
from runway r
where r.airport_id = :airport_id
