import logging
import os
from dotenv import load_dotenv

# Load environment variables to retrieve log paths
load_dotenv()

def setup_logger(name):
    """
    Initializes a standardized logger for the Hurakan App services.
    
    This utility centralizes the logging logic to ensure consistency across 
    different modules. It reads the target log file path from the environment 
    variables and configures both file and console outputs.
    
    Args:
        name (str): The name of the logger (usually the service or module name).
        
    Returns:
        logging.Logger: A configured logger instance.
    """
    
    # Retrieve the log file path from the .env file.
    # Defaults to 'app_activity.log' if the environment variable is missing.
    log_file = os.getenv('APP_LOG_FILE', 'app_activity.log')
    
    # Ensure the directory for the log file exists (crucial for external drive paths)
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger(name)
    
    # Check if handlers are already configured to avoid duplicate log entries
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Standard format: Timestamp - Module Name - Log Level - Message
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        formatter = logging.Formatter(log_format)

        # 1. File Handler: Persists logs to the specified path
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        
        # 2. Stream Handler: Outputs logs to the terminal/console for real-time monitoring
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)

        # Add both handlers to the logger instance
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    return logger

logger = setup_logger("hurakan_app")