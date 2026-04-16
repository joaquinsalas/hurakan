import numpy as np
import pandas as pd
import warnings
from datetime import timedelta
from scipy.ndimage import uniform_filter1d
from skimage.measure import find_contours

# Centralized modular imports
from services.utils.geo_math import (
    haversine_distance, 
    haversine_vectorized, 
    calculate_cluster_dispersion as core_dispersion
)

def calculate_initial_cluster_dispersion(trajectory_list):
    """
    Prepares trajectory data to calculate the mean spatial dispersion.
    
    This function extracts the starting coordinates (Lat, Lon) of each ensemble 
    member and delegates the mathematical calculation to the shared geo_math utility.
    
    Args:
        trajectory_list (list): List of trajectory dictionaries from TempestExtremes.
        
    Returns:
        tuple: (mean_dispersion_km, (centroid_lat, centroid_lon))
    """
    # Extract starting points [lat, lon] for each valid trajectory
    start_points = [[traj[0][1], traj[0][0]] for traj in trajectory_list if traj]
    
    # Delegate to core geo_math utility to ensure a single source of truth
    return core_dispersion(start_points, haversine_distance)

def smooth_lonlat_polygon(coordinates, iterations=2):
    """
    Applies Chaikin's corner-cutting algorithm to smooth polygon boundaries.
    
    Used primarily to make the uncertainty cone visualization look fluid and 
    professional on the Folium map.
    
    Args:
        coordinates (ndarray): Array of [lon, lat] pairs.
        iterations (int): Number of smoothing passes.
        
    Returns:
        ndarray: Smoothed coordinate array.
    """
    if coordinates is None or len(coordinates) < 3: 
        return coordinates
        
    pts = np.asarray(coordinates, dtype=float)
    # Ensure the polygon is closed for consistent smoothing
    if not np.allclose(pts[0], pts[-1], atol=1e-9):
        pts = np.vstack([pts, pts[0]])
        
    for _ in range(iterations):
        point_a, point_b = pts[:-1], pts[1:]
        new_pts = np.empty((len(point_a) * 2, 2))
        # Corner cutting logic: 1/4 and 3/4 points along each segment
        new_pts[0::2] = 0.75 * point_a + 0.25 * point_b
        new_pts[1::2] = 0.25 * point_a + 0.75 * point_b
        pts = np.vstack([new_pts, new_pts[0]])
        
    return pts[:-1]

def calculate_most_probable_trajectory(trajectory_list, step_hours=6, min_members=6, smooth_window=5):
    if not trajectory_list or len(trajectory_list) < min_members: return []
    times = sorted({pt[2] for traj in trajectory_list for pt in traj})
    if not times: return []

    time_grid = []
    curr = times[0]
    while curr <= times[-1]:
        time_grid.append(curr)
        curr += timedelta(hours=step_hours)

    tg_ts = np.array([t.timestamp() for t in time_grid])
    T, M = len(time_grid), len(trajectory_list)
    LON, LAT = np.full((T, M), np.nan), np.full((T, M), np.nan)

    for m, traj in enumerate(trajectory_list):
        if len(traj) < 2: continue
        lons, lats = np.array([p[0] for p in traj]), np.array([p[1] for p in traj])
        ts = np.array([p[2].timestamp() for p in traj])
        _, idx = np.unique(ts, return_index=True)
        if len(idx) < 2: continue
        LON[:, m] = np.interp(tg_ts, ts[idx], lons[idx], left=np.nan, right=np.nan)
        LAT[:, m] = np.interp(tg_ts, ts[idx], lats[idx], left=np.nan, right=np.nan)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        mean_lon = np.nanmean(LON, axis=1)
        mean_lat = np.nanmean(LAT, axis=1)

    valid_count = np.sum(~np.isnan(LON), axis=1)

    # --- THE MAGIC: BIFURCATION AND TELEPORTATION DETECTOR ---
    required_alive = max(3, int(M * 0.3))  # Requires at least 30% active members

    for i in range(1, T):
        # Rule 1: Absolute minimum survival threshold
        if valid_count[i] < required_alive:
            mean_lon[i:] = np.nan
            mean_lat[i:] = np.nan
            break

        # Rule 2: Sudden massive drop off (e.g. hitting land)
        if valid_count[i] < (valid_count[i - 1] * 0.5):
            mean_lon[i:] = np.nan
            mean_lat[i:] = np.nan
            break

        # Rule 3: Velocity limit constraint (prevents backwards jumps)
        if not np.isnan(mean_lon[i]) and not np.isnan(mean_lon[i - 1]):
            dist = haversine_distance(mean_lat[i - 1], mean_lon[i - 1], mean_lat[i], mean_lon[i])
            velocidad_kmh = dist / step_hours
            if velocidad_kmh > 75.0:  # Beyond 75 km/h jump signifies a physically invalid track
                mean_lon[i:] = np.nan
                mean_lat[i:] = np.nan
                break

    mean_lon[valid_count < 2] = np.nan
    mean_lat[valid_count < 2] = np.nan

    # Interpolate inner gaps only, NEVER extrapolate the chopped end
    df = pd.DataFrame({'lon': mean_lon, 'lat': mean_lat}).interpolate(method='linear', limit_area='inside')

    valid_mask = ~df['lon'].isna()
    if not valid_mask.any(): return []

    s_lon = np.full(T, np.nan)
    s_lat = np.full(T, np.nan)

    # Apply smoothing EXCLUSIVELY to the valid segments to prevent twisted edges
    s_lon[valid_mask] = uniform_filter1d(df.loc[valid_mask, 'lon'], size=smooth_window, mode='nearest')
    s_lat[valid_mask] = uniform_filter1d(df.loc[valid_mask, 'lat'], size=smooth_window, mode='nearest')

    return [(float(lo), float(la), dt) for lo, la, dt in zip(s_lon, s_lat, time_grid) if
            not (np.isnan(lo) or np.isnan(la))]

def generate_uncertainty_cone(trajectory_list, mean_track, time_grid, smooth_window=5):
    if not mean_track: return None
    T = len(time_grid)
    if T == 0: return None
    M = len(trajectory_list)
    LON = np.full((T, M), np.nan)
    LAT = np.full((T, M), np.nan)
    tg_ts = np.array([t.timestamp() for t in time_grid])

    for m, traj in enumerate(trajectory_list):
        if len(traj) < 2: continue
        lons = np.array([p[0] for p in traj])
        lats = np.array([p[1] for p in traj])
        ts = np.array([p[2].timestamp() for p in traj])
        _, idx = np.unique(ts, return_index=True)
        if len(idx) < 2: continue
        LON[:, m] = np.interp(tg_ts, ts[idx], lons[idx], left=np.nan, right=np.nan)
        LAT[:, m] = np.interp(tg_ts, ts[idx], lats[idx], left=np.nan, right=np.nan)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        radii_km = np.full(T, np.nan)
        for i in range(T):
            if i >= len(mean_track): break
            m_lon, m_lat, _ = mean_track[i]
            valid = ~np.isnan(LON[i, :])
            if np.any(valid):
                d = haversine_vectorized(m_lon, m_lat, LON[i, valid], LAT[i, valid])
                radii_km[i] = 2 * np.nanstd(d)

    s_r = pd.Series(radii_km).interpolate(method='linear', limit_direction='both').to_numpy()
    s_r = uniform_filter1d(s_r, size=smooth_window, mode='nearest')
    s_r[np.isnan(radii_km)] = np.nan

    valid_idx = ~np.isnan(s_r) & (np.arange(len(s_r)) < len(mean_track))
    if not np.any(valid_idx): return None

    mlon = np.array([p[0] for p in mean_track])[valid_idx]
    mlat = np.array([p[1] for p in mean_track])[valid_idx]
    rr = s_r[valid_idx]

    dlat = rr / 111.1
    coslat = np.cos(np.radians(mlat))
    coslat[coslat < 0.1] = 0.1
    dlon = rr / (111.320 * coslat)

    lon_min = np.min(mlon - dlon)
    lon_max = np.max(mlon + dlon)
    lat_min = np.min(mlat - dlat)
    lat_max = np.max(mlat + dlat)
    pad_lon = (lon_max - lon_min) * 0.1
    pad_lat = (lat_max - lat_min) * 0.1
    lon_min -= pad_lon
    lon_max += pad_lon
    lat_min -= pad_lat
    lat_max += pad_lat

    step_deg = 0.05
    lon_v = np.arange(lon_min, lon_max, step_deg)
    lat_v = np.arange(lat_min, lat_max, step_deg)
    if len(lon_v) < 2 or len(lat_v) < 2: return None

    LonG, LatG = np.meshgrid(lon_v, lat_v)
    mask = np.zeros_like(LonG, dtype=bool)
    for i in range(T):
        if i >= len(mean_track): break
        if np.isnan(s_r[i]): continue
        m_lon, m_lat, _ = mean_track[i]
        dist = haversine_vectorized(m_lon, m_lat, LonG, LatG)
        mask |= (dist <= s_r[i])

    cs = find_contours(mask, 0.5)
    if not cs: return None
    c = max(cs, key=len)
    lats_c = np.interp(c[:, 0], np.arange(len(lat_v)), lat_v)
    lons_c = np.interp(c[:, 1], np.arange(len(lon_v)), lon_v)

    return np.column_stack([lons_c, lats_c])

def filter_trajectory_outliers(trajectory_list, std_dev_threshold=2.0):
    """
    Eliminates ensemble members that significantly deviate from the cluster mean.
    
    Helps in providing cleaner visualizations and more accurate ML features.
    """
    if len(trajectory_list) < 3: return trajectory_list
    mean_trk = calculate_most_probable_trajectory(trajectory_list)
    if not mean_trk: return trajectory_list

    mean_map = {t.timestamp(): (lon, lat) for lon, lat, t in mean_trk}
    mean_ts = np.array(list(mean_map.keys()))

    avg_dists = []
    for traj in trajectory_list:
        dists = []
        for lon, lat, dt, *_ in traj:
            idx = np.argmin(np.abs(mean_ts - dt.timestamp()))
            m_lon, m_lat = mean_map[mean_ts[idx]]
            dists.append(haversine_distance(lat, lon, m_lat, m_lon))
        avg_dists.append(np.max(dists) if dists else np.inf)

    cutoff = np.mean(avg_dists) + std_dev_threshold * np.std(avg_dists)
    return [t for t, d in zip(trajectory_list, avg_dists) if d <= cutoff]