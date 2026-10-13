"""Known radar check-in points for the Xiang'an and Siming campuses."""
import math

METERS_PER_DEGREE_LAT = 111320
XIANGAN_GRID_REACH_M = 60
XIANGAN_GRID_STEP_M = 30
SIMING_GRID_STEP_M = 100
# Drop a later probe when it falls closer than half a Xiang'an step to one
# already queued, so overlapping building rings are not submitted twice.
XIANGAN_DEDUPE_M = XIANGAN_GRID_STEP_M / 2

# OpenStreetMap building-footprint centers, probed in this order.
XIANGAN_BUILDINGS = (
    ("学武楼", 24.608310, 118.309083),
    ("坤銮楼", 24.608400, 118.308034),
    ("文轩楼", 24.608067, 118.305316),
    ("中心区5号楼", 24.607684, 118.304354),
    ("正信楼", 24.606349, 118.295652),
    ("学信楼", 24.607046, 118.295212),
    ("嘉信楼", 24.607398, 118.296236),
    ("启信楼", 24.608109, 118.295517),
    ("智信楼", 24.608340, 118.296771),
    ("睿信楼", 24.609278, 118.295673),
)

SIMING_LAT_MIN = 24.4355753
SIMING_LAT_MAX = 24.4443267
SIMING_LON_MIN = 118.0874946
SIMING_LON_MAX = 118.0989702


def meters_per_degree_lon(latitude):
    return METERS_PER_DEGREE_LAT * math.cos(math.radians(latitude))


def _meters_between(lat1, lon1, lat2, lon2):
    north = (lat1 - lat2) * METERS_PER_DEGREE_LAT
    east = (lon1 - lon2) * meters_per_degree_lon((lat1 + lat2) / 2)
    return math.hypot(north, east)


def _append_if_separated(points, lat, lon, min_meters):
    for kept_lat, kept_lon in points:
        if _meters_between(lat, lon, kept_lat, kept_lon) < min_meters:
            return
    points.append((lat, lon))


def xiangan_probe_points():
    """Building centers first, then a 30 m grid within 60 m of each center."""
    centers = [(lat, lon) for _name, lat, lon in XIANGAN_BUILDINGS]
    points = list(centers)
    offsets = range(-XIANGAN_GRID_REACH_M, XIANGAN_GRID_REACH_M + 1, XIANGAN_GRID_STEP_M)
    for lat, lon in centers:
        lon_scale = meters_per_degree_lon(lat)
        for north in offsets:
            for east in offsets:
                if east == 0 and north == 0:
                    continue
                _append_if_separated(
                    points,
                    lat + north / METERS_PER_DEGREE_LAT,
                    lon + east / lon_scale,
                    XIANGAN_DEDUPE_M,
                )
    return points


def siming_probe_points():
    """100 m grid over the Siming campus bounding box. No priority buildings."""
    points = []
    lat_span = (SIMING_LAT_MAX - SIMING_LAT_MIN) * METERS_PER_DEGREE_LAT
    lat_count = int(math.floor(lat_span / SIMING_GRID_STEP_M + 1e-9)) + 1
    for i in range(lat_count):
        lat = SIMING_LAT_MIN + i * SIMING_GRID_STEP_M / METERS_PER_DEGREE_LAT
        if lat > SIMING_LAT_MAX + 1e-9:
            break
        lon_scale = meters_per_degree_lon(lat)
        lon_span = (SIMING_LON_MAX - SIMING_LON_MIN) * lon_scale
        lon_count = int(math.floor(lon_span / SIMING_GRID_STEP_M + 1e-9)) + 1
        for j in range(lon_count):
            lon = SIMING_LON_MIN + j * SIMING_GRID_STEP_M / lon_scale
            if lon <= SIMING_LON_MAX + 1e-9:
                points.append((lat, lon))
    return points


def probe_points(campus):
    if campus == "xiangan":
        return xiangan_probe_points()
    if campus == "siming":
        return siming_probe_points()
    return []
