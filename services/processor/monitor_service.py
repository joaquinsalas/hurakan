import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv

from services.utils.config import setup_logger
from services.utils.readers import get_timestamp_from_filename, get_region_from_filename
from services.processor.processing import run_main_processing
from services.processor.visualization import generate_combined_map

load_dotenv()
logger = setup_logger("monitorService")

# Global state to track processed basins per cycle
# Format: {"YYYYMMDD_HH": {"atlantico": bool, "pacifico": bool}}
cycle_state = {}

class HurricaneNCSourceHandler(FileSystemEventHandler):
    """
    Handles file system events for NetCDF files.
    Triggers processing and coordinates basin synchronization for mapping.
    """
    def __init__(self, temp_dir, nodes_dir, stitch_dir, output_dir):
        self.temp_dir = temp_dir
        self.nodes_dir = nodes_dir
        self.stitch_dir = stitch_dir
        self.output_dir = output_dir

    def on_closed(self, event):
        if event.is_directory or not event.src_path.endswith(".nc"):
            return
        
        filepath = event.src_path
        filename = os.path.basename(filepath)
        
        timestamp = get_timestamp_from_filename(filename)
        region = get_region_from_filename(filepath)

        if not timestamp or region == 'unknown':
            logger.warning(f"Ignored file (invalid metadata): {filename}")
            return

        logger.info(f"Detected {region} data for cycle {timestamp}. Starting processing...")

        # 1. Execute main processing (TempestExtremes workflow)
        success = run_main_processing(
            filepath, 
            self.temp_dir, 
            self.nodes_dir, 
            self.stitch_dir, 
            region
        )

        if success:
            self._update_state_and_check_completion(timestamp, region)
        else:
            logger.error(f"Processing failed for {filename}. Visualization aborted.")

    def _update_state_and_check_completion(self, timestamp, region):
        """Updates cycle status and triggers visualization if both basins are ready."""
        if timestamp not in cycle_state:
            cycle_state[timestamp] = {"atlantico": False, "pacifico": False}
        
        cycle_state[timestamp][region] = True
        
        atlantico_ready = cycle_state[timestamp]["atlantico"]
        pacifico_ready = cycle_state[timestamp]["pacifico"]

        if atlantico_ready and pacifico_ready:
            logger.info(f"Full cycle synchronization achieved for {timestamp}. Generating map...")
            # Small delay to ensure OS file handles are fully released
            time.sleep(2) 
            
            viz_success = generate_combined_map(
                timestamp, 
                self.stitch_dir, 
                self.output_dir
            )
            
            if viz_success:
                logger.info(f"Cycle {timestamp} fully completed and visualized.")
                del cycle_state[timestamp]
        else:
            missing = "pacifico" if not pacifico_ready else "atlantico"
            logger.info(f"Basin {region} ready. Waiting for {missing} to complete cycle {timestamp}.")

def run_monitor():
    """Configures and starts the directory observer."""
    raw_nc_dir = os.getenv("DATA_RAW_DIR", "./data/raw_nc")
    temp_dir = os.getenv("TEMP_DIR", "./data/temp")
    nodes_dir = os.getenv("NODES_DIR", "./data/nodes_detected")
    stitch_dir = os.getenv("STITCH_DIR", "./data/nodes_stitch")
    output_dir = os.getenv("OUTPUT_DIR", "./data/output")

    # Ensure required directories exist
    for d in [raw_nc_dir, temp_dir, nodes_dir, stitch_dir, output_dir]:
        os.makedirs(d, exist_ok=True)

    event_handler = HurricaneNCSourceHandler(temp_dir, nodes_dir, stitch_dir, output_dir)
    observer = Observer()
    observer.schedule(event_handler, raw_nc_dir, recursive=True)

    logger.info("--------------------------------------------------")
    logger.info("Hurakan Monitor Service is now ACTIVE")
    logger.info(f"Monitoring: {raw_nc_dir}")
    logger.info("Waiting for dual-basin NetCDF files...")
    logger.info("--------------------------------------------------")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Monitor Service stopping...")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    run_monitor()