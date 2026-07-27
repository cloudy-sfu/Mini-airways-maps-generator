select *
from obstacles
where lat >= :south_lat and lat <= :north_lat and
      case
          when :west_lon <= :east_lon
              then lon >= :west_lon and lon <= :east_lon
          else lon >= :west_lon or lon <= :east_lon  -- crosses 180° longitude
      end
  and
    height >= 150
