import numpy as np
from scipy.interpolate import interp1d

def interpolate_trajectories(times, lons, lats, target_times):
    """
    Interpolates a trajectory to a new set of timestamps.
    Used for matching ensemble members with Best Track reference data.
    
    Args:
        times (list/array): Original datetime objects or numerical timestamps.
        lons (list/array): Original longitude values.
        lats (list/array): Original latitude values.
        target_times (list/array): The timestamps to interpolate to.
        
    Returns:
        tuple: (interpolated_lons, interpolated_lats)
    """
    if len(times) < 2:
        return np.array(lons), np.array(lats)

    # Convert datetimes to numerical values for interpolation if necessary
    if hasattr(times[0], 'timestamp'):
        t_orig = np.array([t.timestamp() for t in times])
        t_target = np.array([t.timestamp() for t in target_times])
    else:
        t_orig = np.array(times)
        t_target = np.array(target_times)

    # Create linear interpolation functions
    f_lon = interp1d(t_orig, lons, kind='linear', fill_value="extrapolate")
    f_lat = interp1d(t_orig, lats, kind='linear', fill_value="extrapolate")

    return f_lon(t_target), f_lat(t_target)

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculates a single great-circle distance between two points."""
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1-a))

def haversine_vectorized(lon1, lat1, lon2, lat2):
    """
    Highly optimized vectorized Haversine for RMSE evaluation and cone generation.
    Supports scalars or NumPy arrays.
    """
    R = 6371.0
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculates the bearing (direction) between two points for track arrows."""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    d_lon = lon2 - lon1
    x = np.sin(d_lon) * np.cos(lat2)
    y = np.cos(lat1) * np.sin(lat2) - (np.sin(lat1) * np.cos(lat2) * np.cos(d_lon))
    initial_bearing = np.arctan2(x, y)
    return (np.degrees(initial_bearing) + 360) % 360

def get_saffir_category(wind_ms):
    """Converts wind speed from m/s to Saffir-Simpson category (km/h based)."""
    if wind_ms is None: return 0
    w_kmh = wind_ms * 3.6
    if w_kmh >= 252: return 5
    if w_kmh >= 209: return 4
    if w_kmh >= 178: return 3
    if w_kmh >= 154: return 2
    if w_kmh >= 119: return 1
    if w_kmh >= 63: return 8  # Tropical Storm
    return 7  # Tropical Depression

def get_category_color(cat):
    """Returns the official HEX color for a given Saffir category."""
    colors = {
        5: '#ff6060', 4: '#ff8f20', 3: '#ffc140', 2: '#ffe775',
        1: '#ffffcc', 8: '#00faf0', 7: '#5ebaff', 0: '#cccccc'
    }
    return colors.get(cat, '#cccccc')

def calculate_cluster_dispersion(points_list, haversine_func=None):
    """
    Core mathematical function for spatial dispersion.
    Used by both real-time analysis and historical evaluation.
    """
    if not points_list: return float('inf'), None
    if haversine_func is None: haversine_func = haversine_distance
    
    pts = np.asarray(points_list)
    centroid = pts.mean(axis=0) # [lat, lon]
    dists = [haversine_func(lat, lon, centroid[0], centroid[1]) for lat, lon in pts]
    return float(np.mean(dists)), (centroid[0], centroid[1])