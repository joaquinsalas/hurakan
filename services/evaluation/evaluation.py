import os
import glob
import shutil
import warnings
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime
from collections import defaultdict
from scipy.interpolate import interp1d

# Modular imports from the central utility core
from services.utils.config import setup_logger
from services.utils.geo_math import haversine_vectorized
from services.utils.readers import parse_stitch_file, get_timestamp_from_filename
from services.utils.viz_tools import apply_custom_style, save_plot

# Initialize the evaluation engine logger
logger = setup_logger("evaluationEngine")

class EvaluateTrajectories:
    """
    Evaluates hurricane ensemble forecasts against reference Best Track data.
    Refactored for modular integration with the Hurakan App.
    """

    def __init__(self, hurricane_names, years, ref_csv_path):
        """
        Initializes the evaluation engine with historical reference data.
        """
        if not os.path.exists(ref_csv_path):
            logger.error(f"Reference CSV not found at {ref_csv_path}")
            raise FileNotFoundError

        self.data = pd.read_csv(ref_csv_path)
        self.data['ISO_TIME'] = pd.to_datetime(self.data['ISO_TIME'])
        
        self.hurricanes_data = {}
        self.get_hurricanes(hurricane_names, years)
        logger.info(f"Initialized evaluation for {len(self.hurricanes_data)} hurricanes.")

    def get_hurricanes(self, hurricane_names, years):
        """Filters reference data for specific study cases."""
        for name, year in zip(hurricane_names, years):
            df = self.data[(self.data['SEASON'] == year) & 
                           (self.data['NAME'].str.upper() == name.upper())].copy()
            if not df.empty:
                self.hurricanes_data[name.upper()] = df
            else:
                logger.warning(f"No reference data found for {name} ({year})")

    def assign_trajectories_to_tcs(self, input_folder, output_folder):
        """
        Organizes raw stitched files into hurricane-specific subfolders 
        based on temporal overlap.
        """
        os.makedirs(output_folder, exist_ok=True)
        trajectories_by_h = defaultdict(list)
        
        search_pattern = os.path.join(input_folder, 'nodes_stitch_*.txt')
        files = glob.glob(search_pattern)

        for f_path in files:
            if os.path.getsize(f_path) == 0: continue
            
            # Read blocks using the modular reader
            trajs = parse_stitch_file(f_path)
            if not trajs: continue

            for traj in trajs:
                t_start, t_end = traj[0][2], traj[-1][2]
                
                for h_name, ref_table in self.hurricanes_data.items():
                    ref_start = ref_table['ISO_TIME'].min()
                    ref_end = ref_table['ISO_TIME'].max()

                    # Check for time overlap
                    if t_start <= ref_end and t_end >= ref_start:
                        trajectories_by_h[h_name].append({
                            "content": traj,
                            "filename": os.path.basename(f_path)
                        })

        # Save organized files
        for h_name, data_list in trajectories_by_h.items():
            h_dir = os.path.join(output_folder, h_name)
            if os.path.exists(h_dir): shutil.rmtree(h_dir)
            os.makedirs(h_dir)

            for item in data_list:
                out_path = os.path.join(h_dir, item['filename'])
                # Format to match original TempestExtremes output for consistency
                with open(out_path, 'a') as f:
                    f.write(f"start {len(item['content'])}\n")
                    for p in item['content']:
                        line = f"0 0 {p[0]} {p[1]} {p[3]} {p[4]} {p[5]} {p[2].year} {p[2].month} {p[2].day} {p[2].hour}\n"
                        f.write(line)
        
        logger.info(f"Assigned trajectories to {len(trajectories_by_h)} folders.")

    def evaluate_ensemble(self, input_folder, output_folder, style='dark'):
        """
        Calculates RMSE for each hurricane ensemble and generates performance plots.
        """
        os.makedirs(output_folder, exist_ok=True)
        
        for h_name, ref_table in self.hurricanes_data.items():
            h_input_dir = os.path.join(input_folder, h_name)
            if not os.path.exists(h_input_dir): continue

            # Gather forecast data grouped by cycle (start_key)
            forecast_cycles = self._gather_forecast_data(h_input_dir)
            if not forecast_cycles: continue

            fig, ax = plt.subplots(figsize=(16, 9))
            all_rmse_curves = []
            
            for s_key, data in sorted(forecast_cycles.items()):
                rmse_vals, time_axis = self._compute_cycle_rmse(data, ref_table)
                
                if rmse_vals is not None:
                    ax.plot(time_axis, rmse_vals, label=s_key[6:].replace('_', ':'), lw=1.5)
                    all_rmse_curves.append(pd.Series(rmse_vals, index=time_axis, name=s_key))

            # Styling and Saving
            title = f"RMSE Evolution - {h_name}\nReference: {ref_table['ISO_TIME'].min().year}"
            apply_custom_style(fig, ax, style=style)
            ax.set_xlabel("Hours since forecast start")
            ax.set_ylabel("RMSE (km)")
            ax.legend(ncol=5, fontsize=8, loc='upper left')
            
            save_plot(fig, os.path.join(output_folder, f"RMSE_{h_name}_{style}.png"))
            
            # Export raw data to CSV
            if all_rmse_curves:
                pd.concat(all_rmse_curves, axis=1).to_csv(os.path.join(output_folder, f"RMSE_data_{h_name}.csv"))

    def _compute_cycle_rmse(self, cycle_data, ref_table):
        """Internal helper to calculate RMSE for an entire ensemble cycle."""
        t0 = cycle_data['T0']
        members = cycle_data['members']
        ref_times = pd.to_datetime(ref_table['ISO_TIME'])
        
        # Determine shared time window
        f_start = min([min(m['times']) for m in members])
        f_end = max([max(m['times']) for m in members])
        overlap_mask = (ref_times >= f_start) & (ref_times <= f_end)
        t_common = ref_times[overlap_mask]
        
        if t_common.empty: return None, None

        ref_points = ref_table[overlap_mask]
        sq_errors = np.full((len(members), len(t_common)), np.nan)

        for j, m in enumerate(members):
            m_df = pd.DataFrame({'lon': m['lon'], 'lat': m['lat']}, index=pd.to_datetime(m['times']))
            m_df = m_df[~m_df.index.duplicated()]
            interp = m_df.reindex(t_common).interpolate(method='time')
            
            # Use vectorized haversine from geo_math.py
            dist = haversine_vectorized(interp['lon'].values, interp['lat'].values, 
                                        ref_points['LON'].values, ref_points['LAT'].values)
            sq_errors[j, :] = dist**2

        rmse = np.sqrt(np.nanmean(sq_errors, axis=0))
        hours_axis = (t_common - t0).dt.total_seconds() / 3600.0
        return rmse, hours_axis

    def _gather_forecast_data(self, h_folder):
        """Organizes local stitch files into dictionary cycles."""
        data_by_cycle = {}
        files = glob.glob(os.path.join(h_folder, "nodes_stitch_*.txt"))
        
        for f in files:
            ts = get_timestamp_from_filename(f)
            if not ts: continue
            
            t0 = datetime.strptime(ts, '%Y%m%d_%H')
            s_key = f"S{ts}"
            
            trajs = parse_stitch_file(f)
            for t in trajs:
                if s_key not in data_by_cycle:
                    data_by_cycle[s_key] = {'members': [], 'T0': t0}
                data_by_cycle[s_key]['members'].append({
                    'times': [p[2] for p in t], 'lon': [p[0] for p in t], 'lat': [p[1] for p in t]
                })
        return data_by_cycle