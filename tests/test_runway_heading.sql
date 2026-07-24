select r.primary_lonx
     , r.secondary_lonx
     , r.primary_laty
     , r.secondary_laty
     , r.heading
from runway r
where r.airport_id = :airport_id
