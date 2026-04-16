import os
import re
import pandas as pd
from datetime import datetime, timezone
from services.utils.config import logger

def get_timestamp_from_filename(filename):
    """Safely extracts YYYYMMDD_HH from filename using regex."""
    if not filename: return None
    match = re.search(r"(\d{8})_(\d{2})", filename)
    if match:
        try:
            return f"{match.group(1)}_{match.group(2)}"
        except (IndexError, AttributeError):
            logger.error(f"Error extracting timestamp from filename: {filename}", exc_info=True)
    return None

def get_region_from_filename(filepath):
    """Identifies basin region from path keywords."""
    path_lower = filepath.lower()
    if 'pacifico' in path_lower or 'pacific' in path_lower: return 'pacifico'
    if 'atlantico' in path_lower or 'atlantic' in path_lower: return 'atlantico'
    return 'unknown'

def parse_stitch_file(file_path, file_id=0):
    """
    Parses TempestExtremes stitch files.
    Skips empty files and malformed lines to prevent index errors.
    """
    trajectories = []
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return []
    
    try:
        with open(file_path, 'r') as f:
            current_traj = []
            for line in f:
                parts = line.split()
                if not parts: continue # Skip empty lines

                if parts[0] == "start":
                    if current_traj: trajectories.append(current_traj)
                    current_traj = []
                    continue
                
                # Check for minimum required columns (11) for date parsing
                if len(parts) >= 11:
                    try:
                        # Indices based on provided data: [2]:lon, [3]:lat, [7-10]:date
                        dt = datetime(
                            int(parts[7]), int(parts[8]), 
                            int(parts[9]), int(parts[10]), 
                            tzinfo=timezone.utc
                        )
                        current_traj.append([
                            float(parts[2]), float(parts[3]), dt, 
                            float(parts[4]), float(parts[5]), float(parts[6])
                        ])
                    except (ValueError, IndexError):
                        logger.error(f"Error parsing trajectory date/values in file: {file_path}, line: {line.strip()}", exc_info=True)
                        continue
            
            if current_traj:
                trajectories.append(current_traj)
    except Exception:
        logger.error(f"Error parsing stitch file: {file_path}", exc_info=True)
        
    return trajectories

def get_representative_date(trajectory_list):
    """Returns median start date of a trajectory cluster."""
    if not trajectory_list: return None
    start_dates = [trk[0][2] for trk in trajectory_list if trk and len(trk[0]) >= 3]
    if not start_dates: return None
    return sorted(start_dates)[len(start_dates) // 2]

def load_thresholds_csv(path):
    """Loads CSV with error handling and normalizes column names."""
    try:
        if not path or not os.path.exists(path):
            return pd.DataFrame()
        df = pd.read_csv(path)
        
        low = {c.lower(): c for c in df.columns}
        def pick(*opts):
            for o in opts:
                if o in low: return low[o]
            return None

        c_horas = pick('lead_time_hours', 'horas_diff', 'horas_diff_estimadas', 'lead_hours', 'horas')
        c_link = pick('link_dist_threshold_km', 'link_tol_km', 'umbral_distancia_enlace_km', 'dispersion', 'distancia')
        c_min = pick('min_trajectories_per_cluster', 'min_n', 'umbral_min_trayectorias_por_cluster', 'trayectorias', 'minimo')

        if not all([c_horas, c_link, c_min]): 
            return df # fallback if mapping fails
            
        df = df.rename(columns={c_horas: 'lead_time_hours', c_link: 'link_dist_threshold_km', c_min: 'min_trajectories_per_cluster'})
        
        # Ensure lead time is positive decreasing
        if (df['lead_time_hours'] < 0).all(): 
            df['lead_time_hours'] = -df['lead_time_hours']

        return df.sort_values('lead_time_hours', ascending=False).reset_index(drop=True)
        
    except Exception:
        logger.error(f"Error loading thresholds CSV: {path}", exc_info=True)
    return pd.DataFrame()