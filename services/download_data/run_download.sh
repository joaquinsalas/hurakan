#!/bin/bash
set -e

cd '/home/servertrx/hurakan/services/download_data'

# Si usas entorno virtual:
source '/home/servertrx/hurakan/hurakan_env/bin/activate'

python download_all_nc_nonstop.py