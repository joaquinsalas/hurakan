import os
import redis
import json
import logging

logger = logging.getLogger("redisCache")

def get_redis_client():
    """
    Get a connection to Redis. Uses environmental variables if available,
    otherwise defaults to localhost.
    """
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    try:
        r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True, socket_connect_timeout=2)
        r.ping() # test connection
        return r
    except redis.ConnectionError:
        logger.warning(f"Could not connect to Redis at {redis_host}:{redis_port}. Falling back to non-cached execution.")
        return None

def scan_stitch_directory(stitch_dir):
    """
    Scans the directory for valid timestamps that have both atlantico and pacifico data.
    """
    if not os.path.exists(stitch_dir):
        logger.error(f"Directory {stitch_dir} does not exist.")
        return []

    files = os.listdir(stitch_dir)
    timestamps = {}
    
    for f in files:
        if f.startswith("nodes_stitch_") and f.endswith(".txt"):
            # FORMAT: nodes_stitch_YYYYMMDD_HH_basin_XX.txt
            parts = f.replace(".txt", "").split("_")
            if len(parts) >= 5:
                # parts: ['nodes', 'stitch', 'YYYYMMDD', 'HH', 'basin', 'XX']
                ts = f"{parts[2]}_{parts[3]}"
                basin = parts[4]
                if ts not in timestamps:
                    timestamps[ts] = set()
                timestamps[ts].add(basin)
                
    valid_timestamps = []
    for ts, basins in timestamps.items():
        if "atlantico" in basins and "pacifico" in basins:
            valid_timestamps.append(ts)
        elif "pacifico" in basins:
            valid_timestamps.append(f"{ts} (pacific only)")
        elif "atlantico" in basins:
            valid_timestamps.append(f"{ts} (atlantic only)")
    
    # Sort descending (newest first)
    valid_timestamps.sort(reverse=True)
    return valid_timestamps

def get_available_timestamps(stitch_dir, cache_ttl=300):
    """
    Retrieves available valid timestamps from Redis cache, or scans the directory
    if the cache is missing/expired.
    """
    cache_key = "available_timestamps_all_basins"
    r = get_redis_client()
    
    if r:
        try:
            cached_data = r.get(cache_key)
            if cached_data:
                logger.info("Retrieved valid timestamps from Redis cache.")
                return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Error reading from Redis: {e}")

    # If cache miss, or no Redis available
    logger.info("Cache miss or Redis unavailable. Scanning directory...")
    valid_timestamps = scan_stitch_directory(stitch_dir)
    
    # Try to save back to Redis
    if r:
        try:
            r.setex(cache_key, cache_ttl, json.dumps(valid_timestamps))
            logger.info(f"Saved {len(valid_timestamps)} timestamps to Redis (TTL {cache_ttl}s).")
        except Exception as e:
            logger.error(f"Error writing to Redis: {e}")
            
    return valid_timestamps
