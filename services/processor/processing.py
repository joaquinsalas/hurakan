import os
import glob
import subprocess
import xarray as xr
import numpy as np
import time
import csv
import re
from multiprocessing import Pool
from datetime import datetime
from dotenv import load_dotenv
from services.utils.readers import parse_stitch_file
from services.utils.config import setup_logger

load_dotenv()
logger = setup_logger("processEngine")

def record_performance_csv(metrics):
    perf_log = "data/logs/processing_performance.csv"
    os.makedirs(os.path.dirname(perf_log), exist_ok=True)
    file_exists = os.path.isfile(perf_log)
    headers = ['timestamp', 'file_name', 'region', 'threads', 'total_duration_sec', 'prep_sec', 'detect_stitch_sec', 'trajectories_count']
    try:
        with open(perf_log, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            if not file_exists: writer.writeheader()
            writer.writerow(metrics)
    except Exception as e:
        logger.error(f"CSV Error: {e}")

def count_trajectories(stitch_file):
    if not os.path.exists(stitch_file): return 0
    try:
        with open(stitch_file, 'r') as f:
            return sum(1 for line in f if line.startswith('start'))
    except Exception as e:
        logger.error(f"Error counting trajectories in {stitch_file}: {e}", exc_info=True)
        return 0

def process_single_ensemble_member(args):
    member_index, input_nc_path, temp_dir, nodes_dir, stitch_dir, region = args
    basename = os.path.basename(input_nc_path)
    match = re.search(r'(\d{8})_(\d{2})', basename)
    ts = f"{match.group(1)}_{match.group(2)}" if match else "unknown"

    temp_nc = os.path.join(temp_dir, f"temp_{ts}_{region}_{member_index:02d}.nc")
    nodes_f = os.path.join(nodes_dir, f"nodes_{ts}_{region}_{member_index:02d}.txt")
    stitch_f = os.path.join(stitch_dir, f"nodes_stitch_{ts}_{region}_{member_index:02d}.txt")

    det_exe = os.getenv('DETECT_NODES_PATH', "bin/DetectNodes")
    sti_exe = os.getenv('STITCH_NODES_PATH', "bin/StitchNodes")

    det_cmd = (f"{det_exe} --in_data {temp_nc} --timefilter '6hr' --out {nodes_f} "
               f"--searchbymin mslp --closedcontourcmd 'mslp,200.0,5.5,0;_DIFF(geopotential_300,geopotential_500),-58.8,6.5,1.0' "
               f"--mergedist 6.0 --outputcmd 'mslp,min,0;_VECMAG(u10,v10),max,2;elevation,min,0' "
               f"--latname lat --lonname lon --regional")
    
    sti_cmd = (f"{sti_exe} --in {nodes_f} --out {stitch_f} --in_fmt 'lon,lat,slp,wind,elev' "
               f"--range 6.00 --mintime '24h' --maxgap '36h' --threshold 'wind,>=,10.0,3;lat,<=,45.0,3;lat,>=,-5.0,3'")

    try:
        with xr.open_dataset(input_nc_path) as ds:
            u_times, counts = np.unique(ds["time"].values, return_counts=True)
            num_m = int(counts[0])
            t_idx = [(j * num_m) + member_index for j in range(len(u_times))]
            ds.isel(time=t_idx).to_netcdf(temp_nc, encoding={"time": {"units": "hours since 1970-01-01"}})

        subprocess.run(det_cmd, shell=True, check=True, capture_output=True)
        subprocess.run(sti_cmd, shell=True, check=True, capture_output=True)
        return True
    except Exception as e:
        logger.error(f"Mem {member_index} Error: {e}")
        return False
    finally:
        if os.path.exists(temp_nc): os.remove(temp_nc)

def run_main_processing(input_nc_path, temp_dir, nodes_dir, stitch_dir, region, max_threads=8):
    t_start = time.time()
    try:
        with xr.open_dataset(input_nc_path) as ds:
            _, counts = np.unique(ds["time"].values, return_counts=True)
            num_m = int(counts[0])
        
        t_prep = time.time() - t_start
        n_proc = min(num_m, max_threads)
        
        with Pool(processes=n_proc) as pool:
            tasks = [(i, input_nc_path, temp_dir, nodes_dir, stitch_dir, region) for i in range(num_m)]
            results = pool.map(process_single_ensemble_member, tasks)
        
        match = re.search(r'(\d{8})_(\d{2})', os.path.basename(input_nc_path))
        ts = f"{match.group(1)}_{match.group(2)}" if match else "unknown"
        n_trajs = sum(count_trajectories(f) for f in glob.glob(os.path.join(stitch_dir, f"nodes_stitch_{ts}_{region}_*.txt")))

        record_performance_csv({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'file_name': os.path.basename(input_nc_path),
            'region': region, 'threads': n_proc,
            'total_duration_sec': round(time.time() - t_start, 2),
            'prep_sec': round(t_prep, 2),
            'detect_stitch_sec': round(time.time() - (t_start + t_prep), 2),
            'trajectories_count': n_trajs
        })
        return all(results)
    except Exception as e:
        logger.error(f"Main Error: {e}")
        return False

def collect_trajectories_by_region(stitch_folder, timestamp, region):
    all_t = []
    files = sorted(glob.glob(os.path.join(stitch_folder, f"nodes_stitch_{timestamp}_{region}_*.txt")))
    for i, f_path in enumerate(files):
        all_t.extend(parse_stitch_file(f_path, file_id=i))
    return all_t