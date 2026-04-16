import os
import sys
from dotenv import load_dotenv

# Ensure the root directory is in the path to find services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.processor.visualization import generate_combined_map
from services.utils.config import setup_logger
from services.utils.redis_cache import get_available_timestamps

load_dotenv()
logger = setup_logger("mapGenerator")

def select_timestamp(stitch_dir):
    print("Fetching available timestamps (This might be fast if cached in Redis)...")
    timestamps = get_available_timestamps(stitch_dir)
    
    if not timestamps:
        print("No valid timestamps found with data for both basins.")
        return None
        
    print("\nAvailable Timestamps:")
    for i, ts in enumerate(timestamps):
        print(f"{i}. {ts}")
        
    while True:
        choice = input("\nEnter the number of the cycle you want to generate (or 'q' to quit): ")
        if choice.lower() == 'q':
            return None
        try:
            choice_idx = int(choice)
            if 0 <= choice_idx < len(timestamps):
                return timestamps[choice_idx].split()[0]
            else:
                print("Invalid choice. Please select a valid number.")
        except ValueError:
            print("Please enter a number.")


def main():
    """
    Manually triggers the combined map generation for a specific cycle.
    Usage: python generate_map_only.py YYYYMMDD_HH
    """
    # Paths from .env or defaults
    stitch_dir = os.getenv("STITCH_DIR", "./data/nodes_stitch")
    output_dir = os.getenv("OUTPUT_DIR", "./data/output")
    
    timestamp = select_timestamp(stitch_dir)
    if not timestamp:
        return

    logger.info(f"Manually triggering map generation for cycle: {timestamp}")
    
    # Call the visualization engine directly
    success = generate_combined_map(timestamp, stitch_dir, output_dir)
    
    if success:
        logger.info(f"Success! Map saved in {output_dir}")
    else:
        logger.error(f"Failed to generate map for {timestamp}. Check if .txt files exist in {stitch_dir}")

if __name__ == "__main__":
    main()