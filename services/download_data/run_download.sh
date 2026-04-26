#!/bin/bash
set -e

cd '/mnt/hurakan/services/download_data'

# Si usas entorno virtual:
source '/mnt/hurakan/download_env/bin/activate'

python download_all_nc_nonstop.py