"""
Utility script to initialize the local folder structure for the Hurakan app.
Automatically parses the .env configuration file to identify and construct 
the necessary directory trees for data, logs, databases, and models.
"""

import os
from dotenv import dotenv_values

def generate_folder_structure() -> None:
    """
    Reads the environment variables and creates any missing parent directories 
    required by the application's storage paths.
    """
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_path = os.path.join(root_dir, '.env')

    if not os.path.exists(env_path):
        print("Error: .env file not found.")
        return

    config = dotenv_values(env_path)
    
    path_keywords = ['_DIR', '_FILE', '_CSV', '_PATH']
    exclude_keywords = ['URL', 'EE_', 'PROJECT', 'POLY']
    
    directories = set()

    for key, value in config.items():
        if not value or value.startswith(('http', 'projects/')):
            continue
            
        if any(exclude in key for exclude in exclude_keywords):
            continue

        if any(keyword in key for keyword in path_keywords):
            if '.' in os.path.basename(value):
                target_dir = os.path.dirname(value)
            else:
                target_dir = value
                
            if target_dir and target_dir not in ['.', './']:
                abs_dir = os.path.abspath(os.path.join(root_dir, target_dir))
                directories.add(abs_dir)

    for directory in sorted(directories):
        os.makedirs(directory, exist_ok=True)
        print(f"Created/Verified Directory: {directory}")

if __name__ == "__main__":
    generate_folder_structure()
