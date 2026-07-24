select airport_id
       , lonx
       , laty
from airport
where ident = :icao
    and is_closed = false
