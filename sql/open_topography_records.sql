select request_time
from records
-- See also open_topography.py -> check_rate_limit func -> "cd" variable
where request_time > datetime('now', '-1 day')
order by request_time;