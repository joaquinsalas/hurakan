import os
import glob
import logging
import re
from dotenv import load_dotenv
from services.processor.processing import run_main_processing

load_dotenv()

DATA_RAW_DIR = "/mnt/externo8T/HurricaneData/analisis_maps/"
BASINS = ["atlantico", "pacifico"]

TEMP_DIR = os.getenv("DATA_AUX_DIR", "./data/temp")
NODES_DIR = os.getenv("NODES_DIR", "./data/nodes_detected")
STITCH_DIR = os.getenv("STITCH_DIR", "./data/nodes_stitch")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TestingProcessor")

def is_already_processed(nc_file, basin):
    """
    Verifica si el archivo ya fue procesado buscando el output del miembro 00.
    """
    basename = os.path.basename(nc_file)
    match = re.search(r'(\d{8})_(\d{2})', basename)
    if not match:
        return False
    
    timestamp = f"{match.group(1)}_{match.group(2)}"
    expected_file = os.path.join(STITCH_DIR, f"nodes_stitch_{timestamp}_{basin}_00.txt")
    
    return os.path.exists(expected_file)

def ensure_dirs():
    for d in [TEMP_DIR, NODES_DIR, STITCH_DIR]:
        os.makedirs(d, exist_ok=True)

def run_standalone_test():
    ensure_dirs()
    logger.info("Starting stand-alone testing process...")

    for basin in BASINS:
        dir_name = f"downloaded_nc_{basin}"
        basin_path = os.path.join(DATA_RAW_DIR, dir_name)
        nc_files = glob.glob(os.path.join(basin_path, "*.nc"))
        
        if not nc_files:
            logger.warning(f"No .nc files found in: {basin_path}")
            continue

        nc_files.sort()
        num_processes = max(1, int(os.cpu_count() * 0.75))
        for nc_file in nc_files:
            filename = os.path.basename(nc_file)
            
            if is_already_processed(nc_file, basin):
                logger.info(f"SKIPPING: {filename} (Already processed)")
                continue
            
            try:
                logger.info(f"PROCESSING: {filename}")
                success = run_main_processing(
                    input_nc_path=nc_file,
                    temp_dir=TEMP_DIR,
                    nodes_dir=NODES_DIR,
                    stitch_dir=STITCH_DIR,
                    region=basin,
                    max_threads=num_processes
                )
                
                if success:
                    logger.info(f"SUCCESS: {filename}")
                else:
                    logger.error(f"FAILED: {filename}")
                    
            except Exception as e:
                logger.error(f"Critical error while processing {nc_file}: {e}")

    logger.info("Testing process finished.")

if __name__ == "__main__":
    run_standalone_test()