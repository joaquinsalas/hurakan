# download_all_nc_nonstop.py
# Este programa es una versión del que descarga datos en el watachdog pero ejecutandose
#2do plano de manera indefinida. Regularizando la descarga de datos por su cuenta

#cada 6 horas ejecuta la descarga de la imagen más reciente y la guarda en una carpeta
#primero descarga el pacífico y cuando termina descarga el atlántico

import ee
import xarray as xr
import rioxarray as rxr
import numpy as np
import os
from datetime import datetime, timedelta
import pytz
import time
import re
import io
import logging
import socket
import shutil
import requests
from ee import EEException
from requests.exceptions import ConnectionError, Timeout
from googleapiclient.errors import HttpError
import zipfile
import random
import ssl
import errno
from pathlib import Path
import json

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dask.distributed import Client, LocalCluster #multiprocesamiento

from config import txt_time_dir, token_file, credentials_file, pacific_polygon, atlantic_polygon, log_file, datasets_dir, app_dir #rutas
from config import variables # vars meteorologicas desde WN
from config import project_name, credentials_path #google cloud project
from config import SCOPES, timezone #otros

standar_time_zone = pytz.timezone(timezone)

RETRYABLE_HTTP_STATUS = {500, 502, 503, 504}
RETRYABLE_EXCEPTIONS = (
    socket.gaierror,          # fallo DNS / resolución de nombre
    socket.timeout,           # timeout de socket
    TimeoutError,             # timeout genérico
    ConnectionResetError,     # conexión reiniciada
    BrokenPipeError,
    ssl.SSLError,
    ConnectionError,
    Timeout,
)
RETRYABLE_OS_ERRNOS = {
    errno.ENETUNREACH,   # 101 Network is unreachable
    errno.EHOSTUNREACH,  # 113 No route to host
    errno.ETIMEDOUT,     # 110 Connection timed out
    errno.ECONNRESET,    # 104 Connection reset by peer
    errno.EPIPE,         # 32 Broken pipe
    errno.ENETDOWN,      # 100 Network is down
}

# Excepciones específicas #########################################################################
class IncompleteBlockError(Exception):
    """No hay 250 imágenes en el bloque aún."""
    pass
class RetryExhaustedError(Exception):
    """Se agotaron los reintentos de una operación reintentable."""
    pass
class TimeoutDrive(Exception):
    """No se encontraron las carpetas en Drive después de 3 horas, posible cancelación de tarea o eliminación de carpeta en Drive. Reiniciando secuencia de descarga."""
    pass


#definición de métodos ##########################|##################################################
#Autentica con la API de Google Drive usando OAuth2.
def authenticate_drive():
    while True: #intentará autentificarse hasta tener éxito
        try: 
            creds = None
            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
                    creds = flow.run_local_server(port=0, open_browser=False)

                #guarda el token para futuras ejecuciones
                with open(token_file, 'w') as token: 
                    token.write(creds.to_json())

            logging.info("Autentificado en Google Drive.")
            #return creds
            return build('drive', 'v3', credentials=creds)
        
        # Manejo de excepciones
        except RETRYABLE_EXCEPTIONS as e:
            logging.error(
                "Falló la autenticación con Google Drive debido a un error de red local: %s (%s). "
                "Verifica tu conexión o si el servicio de Google está accesible. Reintentando en 60s.",
                str(e), e.__class__.__name__,
                exc_info=True
            )
            time.sleep(60)
        except OSError as e:
            if is_retryable_os_error(e):
                logging.error("Error de red local en authenticate_drive() (errno=%s): %s (%s). Reintentando en 60s.", getattr(e, "errno", None), str(e), e.__class__.__name__, exc_info=True)
                time.sleep(60)
            else:
                logging.critical(msg, exc_info=True)
                print("ERROR FATAL:", msg)
                raise # No tiene sentido reintentar si hay otro error q
        except HttpError as e:
            if not is_retryable_http_error(e):
                logging.critical(
                    "Falló la autenticación con Google Drive debido a un error fatal del lado de Google: %s (%s). "
                    "Deteniendo el programa.",
                    str(e), e.__class__.__name__,
                    exc_info=True
                )
                raise # No se puede continuar con tipo de errores, no es de nuestr lado
            logging.error(
                "Falló la autenticación con Google Drive debido a un error reiterable del lado de Google: %s (%s). "
                "Reintentando en 60s.",
                str(e), e.__class__.__name__,
                exc_info=True
            )
            time.sleep(60)
        except FileNotFoundError as e:
            msg = (
                f"No se encontró el archivo de credenciales requerido: '{token_file}' o '{credentials_file}'. "
                f"Esto impide la autenticación y es un error fatal: {e.__class__.__name__}: {e}"
            )
            logging.critical(msg, exc_info=True)
            print("ERROR FATAL:", msg)
            raise # No tiene sentido reintentar si falta el archivo de credenciales
        except Exception as e:
            logging.error(
                "Ocurrió una excepción inesperada en authenticate_drive(): %s (%s). "
                "Revisar stack trace para más detalles. Reintentando en 60s.",
                str(e), e.__class__.__name__,
                exc_info=True
            )
            time.sleep(60)

def initialize_GEE():
    while True:
        try: 
            # Load credentials from the file
            with open(credentials_path, 'r') as f:
                creds_dict = json.load(f)
            # Create credentials and refresh
            credentials = Credentials.from_authorized_user_info(
                creds_dict, 
                scopes=['https://www.googleapis.com/auth/earthengine']
            )
            credentials.refresh(Request())
            ee.Initialize(credentials=credentials, project=project_name)
            #ee.Initialize(project=project_name)
            logging.info(f"EarthEngine inicializado para el proyecto: {project_name}")
            break
        except RETRYABLE_EXCEPTIONS as e:
            logging.error("Error de red local al inicializar EE: %s (%s). Reintentando en 60s.", e, e.__class__.__name__, exc_info=True)
        except OSError as e:
            if is_retryable_os_error(e):
                logging.error("Error de red local al inicializar EE (errno=%s): %s (%s). Reintentando en 60s.", getattr(e, "errno", None), str(e), e.__class__.__name__, exc_info=True)
            else:
                raise
        except EEException as e:
            logging.error("Error de Earth Engine al inicializar (%s): %s. Reintentando en 60s.", e.__class__.__name__, str(e), exc_info=True)
        except Exception as e:
            logging.error("Excepción inesperada durante EE.Initialize: %s (%s). Reintentando en 60s.", str(e), e.__class__.__name__, exc_info=True)
        # Esperar 1 min antes de reintentar la inicialización
        time.sleep(60)

def wait_for_stable_connection(test_url="https://www.google.com", checks_required=3, sleep_secs=20, timeout=10):
    consecutive_ok = 0
    while True:
        try:
            response = requests.get(test_url, timeout=timeout)
            if response.status_code == 200:
                consecutive_ok += 1
                logging.debug(
                    "Chequeo de conexión OK (%d/%d).",
                    consecutive_ok, checks_required
                )
                if consecutive_ok >= checks_required:
                    logging.info("Conexión estable recuperada.")
                    return
            else:
                consecutive_ok = 0
                logging.debug("Chequeo de conexión devolvió status %s.", response.status_code)

        except Exception as e:
            consecutive_ok = 0
            logging.warning(
                "Sin conexión estable todavía: %s (%s).",
                str(e), e.__class__.__name__
            )
        time.sleep(sleep_secs)

# repite un proceso si encuntra un error que no está en nuestras manos (como el error 500)
def is_retryable_http_error(e):
    status = getattr(getattr(e, "resp", None), "status", None)
    return status in RETRYABLE_HTTP_STATUS

def is_retryable_os_error(e):
    return isinstance(e, OSError) and getattr(e, "errno", None) in RETRYABLE_OS_ERRNOS

def execute_with_retry(request_factory, *,
                       max_retries=10,
                       base_delay=5,
                       max_delay=300,
                       op_name="operación Drive"):
    """
    request_factory: función sin argumentos que devuelve el request de Google API.
    """
    last_exc = None

    for attempt in range(1, max_retries + 1):
        try:
            request = request_factory()
            return request.execute()

        except HttpError as e:
            last_exc = e
            if not is_retryable_http_error(e):
                raise  # 4xx y otros no reintentables
            delay = min(max_delay, base_delay * (2 ** (attempt - 1))) + random.uniform(0, 1)
            logging.debug(
                "%s falló con HttpError reintentable (%s). Intento %d/%d. "
                "Reintentando en %.1fs.",
                op_name, getattr(e.resp, "status", "sin_status"),
                attempt, max_retries, delay,
                exc_info=True
            )
            time.sleep(delay)

        except RETRYABLE_EXCEPTIONS as e:
            last_exc = e
            delay = min(max_delay, base_delay * (2 ** (attempt - 1))) + random.uniform(0, 1)
            logging.debug(
                "%s falló por red local/transporte (%s). Intento %d/%d. "
                "Reintentando en %.1fs.",
                op_name, e.__class__.__name__,
                attempt, max_retries, delay,
                exc_info=True
            )
            time.sleep(delay)

        except OSError as e:
            if not is_retryable_os_error(e):
                raise
            last_exc = e
            delay = min(max_delay, base_delay * (2 ** (attempt - 1))) + random.uniform(0, 1)
            logging.debug(
                "%s falló con OSError de red local (errno=%s). Intento %d/%d. "
                "Reintentando en %.1fs.",
                op_name, getattr(e, "errno", None),
                attempt, max_retries, delay,
                exc_info=True
            )
            time.sleep(delay)

    raise RetryExhaustedError(
        f"Se agotaron los {max_retries} reintentos en {op_name}: "
        f"{last_exc.__class__.__name__}: {last_exc}"
    )

def find_folder_ids(service, names):
    """
    Busca en el Drive las carpetas con esos nombres y devuelve un dict nombre->ID.
    """
    ids = {}
    for name in names:
        safe_name = name.replace("'", "\\'")
        q = (
            f"mimeType='application/vnd.google-apps.folder' and "
            f"name = '{safe_name}' and trashed = false"
        )
        resp = execute_with_retry(
            lambda: service.files().list(
                q=q,
                spaces='drive',
                fields='files(id,name)'
            ),
            op_name=f"buscar carpeta '{name}'"
        )
        files = resp.get('files', [])
        if not files:
            logging.debug(f"No se encontró ninguna carpeta llamada '{name}'")
        else:
            # toma la primera coincidencia
            folder = files[0]
            ids[name] = folder['id']
            logging.debug(f"Encontrada carpeta '{name}' → ID: {folder['id']}")
            
    return ids

def download_file_with_retry(service, file_id, file_name, save_path, max_retries=8, base_delay=5, max_delay=300):
    target = os.path.join(save_path, file_name)
    last_exc = None

    for attempt in range(1, max_retries + 1):
        try:
            request = service.files().get_media(fileId=file_id)
            with io.FileIO(target, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    try:
                        status, done = downloader.next_chunk()
                        if status is not None:
                            logging.debug("    → %s: %d%%", file_name, int(status.progress() * 100))
                    except HttpError as e:
                        if is_retryable_http_error(e):
                            raise
                        raise
            return
        except HttpError as e:
            last_exc = e
            if not is_retryable_http_error(e):
                raise
        except RETRYABLE_EXCEPTIONS as e:
            last_exc = e

        # si llegó aquí, es reintentable
        if os.path.exists(target):
            try:
                os.remove(target)
            except OSError:
                pass
        delay = min(max_delay, base_delay * (2 ** (attempt - 1))) + random.uniform(0, 1)
        logging.warning(
            "Descarga '%s' falló (%s). Intento %d/%d. Reintentando en %.1fs.",
            file_name, last_exc.__class__.__name__,
            attempt, max_retries, delay,
            exc_info=True
        )
        time.sleep(delay)

    raise RetryExhaustedError(
        f"Se agotaron los reintentos descargando '{file_name}': "
        f"{last_exc.__class__.__name__}: {last_exc}"
    )

def secuencia_descarga_drive(aux_dir, FOLDER_NAMES, service, inicio):
    # Revisa si las carpetas ya existen en el drive
    folder_ids = {}
    while len(folder_ids) != len(FOLDER_NAMES):
        # si lleva más de 3 horas sin encontrar las carpetas, manda una excepción para reiniciar la descarga
        if time.time() - inicio > (3*3600):
            raise TimeoutDrive()
        folder_ids = find_folder_ids(service, FOLDER_NAMES)
        time.sleep(20)

    downloaded = set() #confirmadas las carpetas, esperamos los archivos
    logging.info("Iniciando monitoreo de carpetas por nombre...")

    # 2) bucle principal: cada minuto revisa las carpetas pendientes
    while len(downloaded) < len(folder_ids):
        for name, fid in folder_ids.items():
            if name in downloaded:
                continue

            # lista archivos dentro de la carpeta
            q = f"'{fid}' in parents and trashed=false"
            resp = execute_with_retry(
                lambda: service.files().list(
                    q=q,
                    spaces='drive',
                    fields='files(id,name)'
                ),
                op_name=f"listar archivos en carpeta '{name}'"
            )
            files = resp.get('files', [])

            if files:
                f = files[0]
                logging.info(f"Archivo detectado en '{name}': {f['name']}. Descargando...")
                #download_file(service, f['id'], f['name'], aux_dir)
                download_file_with_retry(service, f['id'], f['name'], aux_dir)
                # borrar el archivo remoto
                #service.files().delete(fileId=f['id']).execute()
                execute_with_retry(
                    lambda: service.files().delete(fileId=f['id']),
                    op_name=f"borrar archivo remoto '{f['name']}'"
                )
                downloaded.add(name)

        if len(downloaded) < len(folder_ids):
            logging.debug("Esperando 60s a que las task terminen y que los archivos esten disponibles en drive")
            time.sleep(60)

def check_files_before_download(task_names, aux_dir, FOLDER_NAMES, service, inicio):
    while True:
        # Chequea cuáles archivos aún no existen
        missing = [
            fname for fname in task_names
            if not os.path.exists(os.path.join(aux_dir, fname))
        ]
        if not missing:
            # Si no falta ninguno, salimos del bucle
            logging.info("Todos los archivos están presentes.")
            break

        #empieza la secuencia de descarga de archivos desde drive
        secuencia_descarga_drive(aux_dir, FOLDER_NAMES, service, inicio)

        # Si aún faltan, informamos y esperamos
        logging.debug(f"Faltan archivos: {missing}. Reintentando en 20 s…")
        time.sleep(20)

def define_date(now_mexico):
    # Encontrar el último horario anterior a la hora actual
    horarios = [0, 6, 12, 18]
    ultimo_horario = max([h for h in horarios if h <= now_mexico.hour])

    # Si al restar 6 horas se cruza al día anterior, restar un día
    if ultimo_horario - 6 < 0:
        init_date_utc = now_mexico - timedelta(days=1)
    else:
        init_date_utc = now_mexico

    #  Construir la fecha final con el nuevo horario
    #nuevo_horario = (ultimo_horario - 6) % 24
    init_date_utc = now_mexico.replace(hour=ultimo_horario, minute=0, second=0, microsecond=0)
    init_date_utc_str = init_date_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    return init_date_utc_str

def get_surface_elevation(now_mexico, region_roi, zona, task_names, FOLDER_NAMES):
    """
    Exporta la imagen más reciente de 'Geopotential_height_surface' del último mes a Google Drive
    como GeoTIFF, recortado a una región específica.
    """
    #definir rango de fechas
    fecha_actual = now_mexico.strftime('%Y-%m-%d')
    fecha_inicio = (now_mexico - timedelta(days=30)).strftime('%Y-%m-%d') #restar un mes

    logging.debug("Downloading surface geopotential height from CFSV2...")

    try: 

        #toma la imágen más reciente del "Geopotential_height_surface" en el último mes
        surface_geopotential = (
            ee.ImageCollection("NOAA/CFSV2/FOR6H")
            .select("Geopotential_height_surface")
            .filterDate(fecha_inicio, fecha_actual)  
            .sort("system:time_start", False)  # Orden descendente para obtener la imagen más reciente
            .first()  # Toma la última imagen disponible
        ).setDefaultProjection("EPSG:4326", None, 25000)  # Fix projection issue

        # Obtener la fecha y hora exactas de la imagen
        timestamp = surface_geopotential.get("system:time_start").getInfo()  # Obtener timestamp en milisegundos
        image_datetime = datetime.utcfromtimestamp(timestamp / 1000)  # Convertir a datetime en UTC

        logging.debug(f"Using Geopotential Height Surface from: {image_datetime} UTC")

        # Clip al área de interés
        surface_geopotential_clipped = surface_geopotential.clip(region_roi)
        # Definir nombre del archivo y el folder
        fecha_str = now_mexico.strftime('%Y%m%d_%H')
        file_name = f"surface_elevation_{fecha_str}_{zona}"
        folder_name = f"EarthEngineForecasts_{fecha_str}_surface_{zona}"

        # Exportar a Google Drive
        task = ee.batch.Export.image.toDrive(
            image=surface_geopotential_clipped,
            description=f"ExportSurfaceElevation_{fecha_str}_{zona}",
            folder=folder_name,
            fileNamePrefix=file_name,
            scale=25000,
            region=region_roi.bounds().getInfo()["coordinates"],
            crs="EPSG:4326",
            maxPixels=1e13
        )
        task.start()

        FOLDER_NAMES.append(folder_name)  # Agregar el nombre del folder a la lista
        task_names.append(file_name + ".tif")  # Agregar el nombre del archivo a la lista
        logging.info(f"Tarea enviada a Google Drive con nombre: '{file_name}'")
        return task_names, FOLDER_NAMES

    except EEException as e:
        raise
    except RETRYABLE_EXCEPTIONS as e:
        raise
    except IncompleteBlockError:
        raise
    except HttpError as e:
        raise
    except Exception as e:
        logging.error(
            "Error inesperado en export_forecast_block_to_drive(): %s (%s)",
            str(e), e.__class__.__name__,
            exc_info=True
        )
        raise

#guarda el tiempo en que tardó descargarse cada archivo en la ultima linea de un txt
def log_time(segundos, archivo_nc):
    # Crea la carpeta si no existe
    os.makedirs(os.path.dirname(txt_time_dir), exist_ok=True)
    # si el txt no existe, lo crea con la cabecera
    if not os.path.exists(txt_time_dir):
        with open(txt_time_dir, 'w') as f:
            f.write("filename,download_time_mins\n")
        os.chmod(txt_time_dir, 0o777)
        logging.info(f"Archivo creado: {txt_time_dir}")

    archivo_name = archivo_nc.split('/')[-1] 
    with open(txt_time_dir, "a") as f:  # 'a' agrega la linea al final del archivo
        f.write(f"{archivo_name},{segundos/60} mins\n")

def export_forecast_block_to_drive(now_mexico, region_roi, zona, FOLDER_NAMES):
    #define el rango de horas de pronóstico para cada bloque
    forecast_ranges = [[0, 60], [72, 120], [132, 180], [192, 240], [252, 300], [312, 360]]
    task_names = []

    try: 
        for i in range(len(forecast_ranges)):
            init_date_utc = define_date(now_mexico)
            #init_date_utc= '2026-02-02T18:00:00Z'
            logging.debug(f"Exportando bloque {i} desde {forecast_ranges[i][0]}h hasta {forecast_ranges[i][1]}h")

            dataset = (
                ee.ImageCollection("projects/gcp-public-data-weathernext/assets/weathernext_2_0_0")
                .filter(ee.Filter.date(init_date_utc))
                .filter(ee.Filter.gte('forecast_hour', forecast_ranges[i][0]))
                .filter(ee.Filter.lte('forecast_hour', forecast_ranges[i][1]))
                .select(list(variables.keys()))
            )

            num_images = dataset.size().getInfo()
            #el bloque 0 debe de tener 640 imagenes y los demás 576 para poder continuar
            if (i == 0 and num_images < 640) or (i > 0 and num_images < 576): 
                raise IncompleteBlockError()

            # Combina todas las imágenes en una sola multibanda
            image_bands = dataset.toBands()
            # Reproyectar si es necesario
            image_bands = image_bands.reproject(crs="EPSG:4326", scale=25000)

            # Definir nombre del archivo y del folder
            date_str = now_mexico.strftime('%Y%m%d_%H')
            file_name = f"forecast_{date_str}_block{i}_{zona}"
            folder_name = f"EarthEngineForecasts_{date_str}_block{i}_{zona}"

            # Exportar a Google Drive como GeoTIFF
            task = ee.batch.Export.image.toDrive(
                image=image_bands.clip(region_roi),
                description=f"ExportForecastBlock_{i}_{date_str}_{zona}",
                folder=folder_name,
                fileNamePrefix=file_name,
                scale=25000,
                region=region_roi.bounds().getInfo()['coordinates'],
                crs='EPSG:4326',
                maxPixels=1e13
            )
            task.start()
            logging.info(f"Tarea enviada a Google Drive con nombre: {file_name}")
            
            FOLDER_NAMES.append(folder_name)  # Agregar el nombre del folder a la lista
            task_names.append(file_name + ".tif")  # Agregar el nombre del archivo a la lista
        #regresa la lista de archivos a descargar del folfer de google drive
        return task_names, FOLDER_NAMES
    except EEException as e:
        raise
    except RETRYABLE_EXCEPTIONS as e:
        raise
    except IncompleteBlockError:
        raise
    except HttpError as e:
        raise
    except Exception as e:
        logging.error(
            "Error inesperado en export_forecast_block_to_drive(): %s (%s)",
            str(e), e.__class__.__name__,
            exc_info=True
        )
        raise

def _convert_tif_subset_to_netcdf(tif_files, output_netcdf):
    """
    Convierte un subconjunto de TIFFs a un NetCDF temporal.
    Basado en tu método original, pero usado para procesar menos bloques a la vez.
    """
    if not tif_files:
        raise ValueError("La lista de archivos .tif está vacía. Nada que convertir.")

    var_name_map = {
        'mean_sea_level_pressure': 'mslp',
        '10m_u_component_of_wind': 'u10',
        '10m_v_component_of_wind': 'v10',
        '300_geopotential': 'geopotential_300',
        '500_geopotential': 'geopotential_500'
    }
    expected_vars = list(var_name_map.values())

    band_regex = re.compile(
        r'(\d{12})_(\d{12})_\d+_'
        r'(mean_sea_level_pressure|10m_u_component_of_wind|'
        r'10m_v_component_of_wind|300_geopotential|500_geopotential)'
    )

    cluster = LocalCluster(
        n_workers=4,
        threads_per_worker=2,
        memory_limit="6GB",
        dashboard_address=":9999"
    )
    client = Client(cluster)

    data_arrays = {var: [] for var in expected_vars}
    time_hours = []
    lat_vals = None
    lon_vals = None

    try:
        for tif_path in tif_files:
            logging.info(f"Leyendo subconjunto TIFF: {tif_path}")
            da = rxr.open_rasterio(
                tif_path,
                masked=True,
                chunks={"band": 50, "y": 256, "x": 256}
            )
            da = da.rename({'band': 'band', 'y': 'lat', 'x': 'lon'})

            if da.lat.values[0] < da.lat.values[-1]:
                da = da.sel(lat=da.lat[::-1])

            try:
                band_names = list(da.descriptions)
            except Exception:
                bm = da.attrs.get("long_name", da.attrs.get("description", None))
                if isinstance(bm, (list, tuple)):
                    band_names = list(bm)
                else:
                    raise ValueError(
                        f"El tif no tiene nombres de bandas en 'descriptions' ni 'attrs'. Intentar volver a descargar"
                    )

            for idx in range(da.sizes["band"]):
                raw_name = band_names[idx]
                m = band_regex.search(raw_name)
                if not m:
                    continue

                date_str_12 = m.group(2)
                var_raw = m.group(3)
                var_short = var_name_map[var_raw]

                dt = datetime.strptime(date_str_12, "%Y%m%d%H%M")
                epoch = datetime(1970, 1, 1)
                delta = dt - epoch
                forecast_hr = int(delta.total_seconds() // 3600)

                layer_2d = da.isel(band=idx)
                layer_2d.attrs.clear()

                data_arrays[var_short].append(layer_2d)

                if var_short == "mslp":
                    time_hours.append(forecast_hr)

                if lat_vals is None:
                    lat_vals = da.lat.values
                    lon_vals = da.lon.values

        ds = xr.Dataset(
            coords={
                "time": ("time", np.array(time_hours, dtype=int)),
                "lat": ("lat", lat_vals),
                "lon": ("lon", lon_vals)
            }
        )
        ds["time"].attrs["units"] = "hours since 1970-01-01 00:00:00"
        ds["time"].attrs["calendar"] = "proleptic_gregorian"

        for var_short in expected_vars:
            if not data_arrays[var_short]:
                continue

            da_concat = xr.concat(data_arrays[var_short], dim="band")
            da_concat = da_concat.rename({"band": "time"})
            da_concat["time"] = ds["time"]

            ds[var_short] = da_concat

        if "spatial_ref" in ds:
            ds = ds.drop_vars("spatial_ref")

        for v in list(ds.data_vars):
            ds[v].attrs.pop("_FillValue", None)
            ds[v].attrs.pop("grid_mapping", None)

        encoding = {
            v: {
                "zlib": True,
                "complevel": 4,
                "chunksizes": (1, 128, 128),
                "_FillValue": np.nan,
                "dtype": "float32",
            }
            for v in ds.data_vars
        }

        ds.to_netcdf(output_netcdf, engine="netcdf4", encoding=encoding)
        logging.info(f"NetCDF temporal guardado en {output_netcdf}")

    except Exception as e:
        logging.error(
            "Error inesperado en _convert_tif_subset_to_netcdf: %s (%s)",
            str(e), e.__class__.__name__,
            exc_info=True
        )
        raise
    finally:
        client.close()
        cluster.close()


def convert_forecast_tifs_to_netcdf(tif_files, output_netcdf):
    """
    Convierte los 6 TIFF en dos NetCDF temporales:
      - TIFF 0,1,2 -> temp_part1.nc
      - TIFF 3,4,5 -> temp_part2.nc
    Luego concatena ambos por time y guarda el NetCDF final.
    """
    if not tif_files:
        raise ValueError("La lista de archivos .tif está vacía. Nada que convertir.")

    if len(tif_files) < 6:
        raise ValueError(
            f"Se esperaban al menos 6 TIFFs, pero solo llegaron {len(tif_files)}."
        )

    temp_nc_1 = output_netcdf.replace(".nc", "_part1.nc")
    temp_nc_2 = output_netcdf.replace(".nc", "_part2.nc")

    try:
        # Primera mitad: bloques 0,1,2
        _convert_tif_subset_to_netcdf(tif_files[:3], temp_nc_1)

        # Segunda mitad: bloques 3,4,5
        _convert_tif_subset_to_netcdf(tif_files[3:6], temp_nc_2)

        logging.info("Abriendo NetCDFs temporales para unirlos...")
        ds1 = xr.open_dataset(temp_nc_1, chunks={"time": 1, "lat": 128, "lon": 128})
        ds2 = xr.open_dataset(temp_nc_2, chunks={"time": 1, "lat": 128, "lon": 128})

        ds_final = xr.concat([ds1, ds2], dim="time")
        ds_final = ds_final.sortby("time")

        for v in list(ds_final.data_vars):
            ds_final[v].attrs.pop("_FillValue", None)
            ds_final[v].attrs.pop("grid_mapping", None)

        encoding = {
            v: {
                "zlib": True,
                "complevel": 4,
                "chunksizes": (1, 128, 128),
                "_FillValue": np.nan,
                "dtype": "float32",
            }
            for v in ds_final.data_vars
        }

        ds_final.to_netcdf(output_netcdf, engine="netcdf4", encoding=encoding)
        logging.info(f"Guardado Weather Next NetCDF final en {output_netcdf}")

        ds1.close()
        ds2.close()
        ds_final.close()

        # borrar temporales
        if os.path.exists(temp_nc_1):
            os.remove(temp_nc_1)
        if os.path.exists(temp_nc_2):
            os.remove(temp_nc_2)

    except Exception as e:
        logging.error(
            "Error inesperado en convert_forecast_tifs_to_netcdf: %s (%s)",
            str(e), e.__class__.__name__,
            exc_info=True
        )
        raise


def add_elevation(nc_file, elevation_tif, output_file):
    # Cargar archivo nc con todas las variables y el tiff de elevation
    ds = xr.open_dataset(nc_file)
    elev_raster = rxr.open_rasterio(elevation_tif, masked=True).squeeze("band")
    elev_raster = elev_raster.rename({'y': 'lat', 'x': 'lon'})

    # Invertir latitud si es necesario
    if elev_raster.lat[0] < elev_raster.lat[-1]:
        elev_raster = elev_raster.sel(lat=elev_raster.lat[::-1])

    # Validar forma
    if (elev_raster.shape != (ds.dims["lat"], ds.dims["lon"])):
        raise ValueError(f"La forma de la elevación {elev_raster.shape} no coincide con el NetCDF {(ds.dims['lat'], ds.dims['lon'])}")

    # Agregar al Dataset
    ds["elevation"] = (["lat", "lon"], elev_raster.values)
    ds["elevation"].attrs["units"] = "meters"
    ds["elevation"].attrs["long_name"] = "Surface elevation from CFSV2"
    ds["elevation"].attrs["_FillValue"] = np.nan
    
    # Guardar nuevo archivo
    ds.to_netcdf(output_file)
    os.chmod(output_file, 0o777)
    logging.info("Elevación añadida correctamente al NetCDF. Archivo final guardado")

def vaciar_drive(service):
    """
    Borra todas las carpetas de Google Drive cuyo nombre tenga el formato: 'EarthEngineForecasts_YYYYMMDD_HH_...'
    Elimina permanentemente todos los archivos que están en la papelera de Google Drive.
    """
    logging.info("Buscando carpetas con nombre tipo 'EarthEngineForecasts_YYYYMMDD_HH_' para eliminarlas...")
    pattern = re.compile(r"^EarthEngineForecasts_\d{8}_\d{2}_")
    try:
        # Obtener todas las carpetas cuyo nombre contiene "EarthEngineForecasts_"
        q="mimeType='application/vnd.google-apps.folder' and name contains 'EarthEngineForecasts_' and trashed = false"
        response = execute_with_retry(
            lambda: service.files().list(
                q=q,
                spaces='drive',
                fields='files(id,name)'
            ),
            op_name=f"listar carpetas con nombre tipo 'EarthEngineForecasts_' para eliminación"
        )

        folders = response.get('files', [])
        if not folders:
            logging.debug("No se encontraron carpetas que coincidan con el patrón.")
        else:
            for folder in folders:
                name = folder['name']
                fid = folder['id']

                if pattern.match(name):
                    try:
                        #service.files().delete(fileId=fid).execute()
                        execute_with_retry(
                            lambda: service.files().delete(fileId=fid),
                            op_name=f"borrar archivo remoto '{name}'"
                        )
                        logging.info(f"Carpeta eliminada: '{name}' (ID: {fid})")
                    except HttpError as e:
                        logging.error(
                            "No se pudo eliminar la carpeta '%s' (ID: %s): %s (%s). "
                            "Esto puede deberse a permisos insuficientes, que ya fue eliminada, "
                            "o un error en la API. Se continuará con las demás.",
                            name, fid, str(e), e.__class__.__name__,
                            exc_info=True
                        )
                else:
                    logging.debug(f"Carpeta ignorada (no coincide con el patrón): '{name}'")
    except HttpError as e:
        logging.error(
            "Error HTTP al listar carpetas de Google Drive para eliminación: %s (%s)",
            str(e), e.__class__.__name__,
            exc_info=True
        )      
    except Exception as e:
        logging.error(
            "Error inesperado al listar carpetas de Google Drive para eliminación: %s (%s).",
            str(e), e.__class__.__name__,
            exc_info=True
        )


    logging.info("Vaciando papelera de Google Drive...")
    try:
        while True:
            # Listar archivos en la papelera
            q="trashed = true"
            response = execute_with_retry(
                lambda: service.files().list(
                    q=q,
                    spaces='drive',
                    fields="nextPageToken, files(id, name)"
                ),
                op_name=f"listar archivos en la papelera"
            )

            files = response.get('files', [])
            if not files:
                break
            for file in files:
                try:
                    #service.files().delete(fileId=file['id']).execute()
                    execute_with_retry(
                        lambda: service.files().delete(fileId=file['id']),
                        op_name=f"borrar archivo remoto '{file['name']}'"
                    )
                except (HttpError, RetryExhaustedError) as e:
                    logging.warning(
                        "No se pudo eliminar el archivo '%s' (ID: %s) de la papelera: %s (%s). "
                        "Puede deberse a un problema de permisos, red, o que ya fue eliminado.",
                        file.get('name', 'desconocido'), file.get('id', 'sin ID'), str(e), e.__class__.__name__,
                        exc_info=True
                    )
            # Continuar si hay más archivos en la siguiente página
            if 'nextPageToken' not in response:
                break
    except HttpError as error:
        logging.error(
            "Error HTTP al intentar listar o procesar archivos en la papelera de Google Drive: %s (%s). "
            "No se pudieron recuperar o eliminar elementos. Revisar la conexión o permisos.",
            str(error), error.__class__.__name__,
            exc_info=True
        )
    except Exception as e:
        logging.error(
            "Error inesperado al intentar listar o procesar archivos en la papelera de Google Drive: %s (%s).",
            str(e), e.__class__.__name__,
            exc_info=True
        )

def borrar_archivos(output_dir, aux_dir, inicio,service, output_file):
    # Eliminar todos los archivos del directorio final excepto el que acabamos de crear
    for file in os.listdir(output_dir):
        file_path = os.path.join(output_dir, file)
        if file_path != output_file and os.path.isfile(file_path):
            os.remove(file_path)
    
    #eliminar los archivos auxiliares
    for file in os.listdir(aux_dir):
        file_path = os.path.join(aux_dir, file)
        if os.path.isfile(file_path):
            os.remove(file_path)

    #calcular le tiempo que tardó todo el proceso
    fin = time.time()  # Fin del contador
    duracion = fin - inicio # tiempo que tardó en descargarse el archivo
    log_time(duracion, output_file)

    # borrar las carpetas tipo 'EarthEngineForecasts_YYYYMMDD_HH_' y vaciar la papelera de drive
    vaciar_drive(service)

#descarga un archivo mediante un url, si es zip lo descomprime
def download_zip(url, output_dir, type):
    # Crear directorio si no existe
    try:
        # borrar todo lo del directorio antes de hacer la descarga
        for filename in os.listdir(output_dir):
            file_path = os.path.join(output_dir, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)

        filename = url.split("/")[-1]
        zip_path=f'{output_dir}/{filename}'

        # Descargar el archivo
        response = requests.get(url, timeout=20)
        if response.status_code != 200:
            print()
            logging.error(
                "No se pudo descargar el archivo shp de zonas de probabilidad de TC",
                str(e), e.__class__.__name__,
                exc_info=True
            )
            return
        with open(zip_path, "wb") as f: #con éxito
            f.write(response.content)
        logging.info("shp_files ed NOAA descargados correctamente")

        # descomprime si es zip
        if type == 'zip': 
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(output_dir)
                os.remove(zip_path)
            except zipfile.BadZipFile: # zip corrupto
                logging.error(
                    "El archivo zip está corrupto o no es un zip válido.",
                    str(e), e.__class__.__name__,
                    exc_info=True
                )
                return
        
        # Dar permisos 777 a todos los archivos extraídos
        for root, dirs, files in os.walk(output_dir):
            for name in files:
                os.chmod(os.path.join(root, name), 0o777)
            for name in dirs:
                os.chmod(os.path.join(root, name), 0o777)
    
    except requests.exceptions.RequestException as e:
        logging.error(
            "Error de red al descargar shp de zonas de probabilidad de TC",
            str(e), e.__class__.__name__,
            exc_info=True
        )
    except Exception as e:
        logging.error(
            "Error inesperado al descargar shp de zonas de probabilidad de TC",
            str(e), e.__class__.__name__,
            exc_info=True
        )  

def get_now_time():
    horarios_permitidos = {0, 6, 12, 18}
    # Obtener la hora actual en la zona horaria de México
    now_mexico = datetime.now(standar_time_zone)
    #restar 6 horas a now_mexico por el UTC y porque ahora hay un delay mucho mayor entre la hora de corte y la disponibilidad de los datos, entonces así nos aseguramos que ya estén disponibles
    now_mexico = now_mexico - timedelta(hours=6)
    ultimo_horario = max([h for h in horarios_permitidos if h <= now_mexico.hour])
    now_mexico = now_mexico.replace(hour=ultimo_horario, minute=0, second=0, microsecond=0) #el bueno
    #now_mexico = now_mexico.replace(hour=0, minute=0, second=0, microsecond=0)
    # crear el nombre de archivo si está dentro del horario permitido
    fecha_string = now_mexico.strftime('%Y%m%d_%H')
    return now_mexico, fecha_string

# main ##########################################################################################
def main():
    # Setup logging (solo se escribirán los logs de INFO en adelante)
    logging.basicConfig(filename=log_file, level=logging.INFO,
                        format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    logging.info('================================================================================================\n' + "Iniciando script de descarga de datos de Weather Next")


    #declaración de variables
    FOLDER_NAMES = []

    # Initialize Google Earth Engine (reintenta si no hay conexión)
    initialize_GEE()
    # #autentificar en google drive
    service = authenticate_drive()
    
    last_hour = None
    while True:
        # Busca los archivos de cada zona
        zonas = ['atlantico', 'pacifico']
        for zona in zonas:
            # Definir directorios dependiendo de la zona
            aux_dir = os.path.join(app_dir, f'auxiliary_files_{zona}')
            output_dir = os.path.join(datasets_dir, zona)
            # Crea los directorios si no existen
            os.makedirs(aux_dir, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)
            os.chmod(aux_dir, 0o777)
            os.chmod(output_dir, 0o777)

            #limina lo que pueda haber en las carpetas auxiliares, en caso de que estemos despertando de un corte de luz
            for file in os.listdir(aux_dir):
                file_path = os.path.join(aux_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)

            while True: #reintentar indefinidamente cada zona hasta que se descargue correctamente
                try:
                    now_mexico, fecha_string = get_now_time()
                    output_file = os.path.join(output_dir, f'regional_weathernext_{fecha_string}_{zona}.nc') #el archivo final
                    # si el archivo más reciente no existe, es necesario descargarlo
                    if not os.path.exists(output_file):
                        # Define el polígono
                        if zona == 'pacifico':
                            region_roi = ee.FeatureCollection(pacific_polygon).geometry() #region atlántico
                        elif zona == 'atlantico':
                            region_roi = ee.FeatureCollection(atlantic_polygon).geometry() #region atlántico

                        FOLDER_NAMES.clear()  # Limpiar la lista de nombres de carpetas
                        inicio = time.time()  # Inicio del contador de tiempo

                        # crean las task de que el bloque se cargue en google drive
                        task_names, FOLDER_NAMES= export_forecast_block_to_drive(now_mexico, region_roi, zona, FOLDER_NAMES)

                        #descarga como un tiff la surface elevation
                        task_names, FOLDER_NAMES = get_surface_elevation(now_mexico, region_roi, zona, task_names, FOLDER_NAMES) 
                        
                        ##########################################################
                        check_files_before_download(task_names, aux_dir, FOLDER_NAMES, service, inicio)
                        #########################################################################

                        #agregar la ruta de los archivos a la lista de tareas (menos el de surface_elevation)
                        task_names = [os.path.join(aux_dir, name) for name in task_names]
                        task_names = [t for t in task_names if 'surface_elevation' not in os.path.basename(t)]

                        #convertir el par de tiff en un solo netcdf
                        nc_file_WN = os.path.join(aux_dir, f'regional_weathernext_{fecha_string}.nc')
                        convert_forecast_tifs_to_netcdf(task_names, nc_file_WN)

                        # a este nc agregarle la elevation
                        add_elevation(nc_file_WN, os.path.join(aux_dir, f'surface_elevation_{fecha_string}_{zona}.tif'), output_file)

                        #eliminación de archivos temporales y calculo del tiempo
                        borrar_archivos(output_dir, aux_dir, inicio, service, output_file)

                        #finish_download += 1
                        logging.info(f"Descarga de {output_file} finalizada.")
                        break
                    else:
                        logging.debug(f"El archivo {output_file} ya existe, no es necesario descargar.")

                except IncompleteBlockError:
                    logging.debug(
                        "Bloque incompleto: No son 250/640/576 imágenes. Reintentando en 60s."
                    )
                except TimeoutDrive as e:
                    logging.error(
                        "No se encontraron las carpetas en Drive después de 3 horas, posible cancelación de tarea o eliminación de carpeta en Drive. Reiniciando secuencia de descarga."
                    )
                    break
                except RetryExhaustedError as e:
                    logging.error(
                        "Fallo transitorio detectado en zona '%s': %s. Revisando conexión",
                        zona, str(e), exc_info=True
                    )
                    wait_for_stable_connection()
                except RETRYABLE_EXCEPTIONS as e:
                    logging.error(
                        "Error debido a un error de red local: %s (%s). "
                        "Verifica tu conexión. Reintentando en 60s.",
                        str(e), e.__class__.__name__,
                        exc_info=True
                    )
                except OSError as e:
                    if is_retryable_os_error(e):
                        logging.error(
                            "Error de red local (OSError errno=%s): %s (%s). "
                            "Revisando conexión.",
                            getattr(e, "errno", None), str(e), e.__class__.__name__,
                            exc_info=True
                        )
                        wait_for_stable_connection()
                    else:
                        raise
                except EEException as e:
                    logging.error(
                        "Error de Earth Engine: %s (%s). "
                        "Revisar parámetros de exportación o cuotas de uso. Reintentando en 60s.",
                        str(e), e.__class__.__name__,
                        exc_info=True
                    )
                except HttpError as e:
                    if not is_retryable_http_error(e):
                        logging.critical(
                            "Error fatal del lado de Google: %s (%s). "
                            "Deteniendo el programa.",
                            str(e), e.__class__.__name__,
                            exc_info=True
                        )
                        raise # No se puede continuar con tipo de errores, no es de nuestr lado
                    else:
                        logging.error(
                            "Error HTTP transitorio: %s (%s). "
                            "Reintentando en 60s.",
                            str(e), e.__class__.__name__,
                            exc_info=True
                        )
                except Exception as e:
                    logging.error(
                        "Error inesperado: %s (%s). Reintentando en 60s.",
                        str(e), e.__class__.__name__,
                        exc_info=True
                    )
                time.sleep(60) #espera para las excepciones

        #cada vez que el minuto actual sea 1,2 o 3, intenta descargar los shp_files de probabilidad de ciclones
        try:
            now_mexico = datetime.now(standar_time_zone)
            output_shp_dir = os.path.join(datasets_dir, "NOAA_files")
            if not os.path.exists(output_shp_dir):
                os.makedirs(output_shp_dir, exist_ok=True)
                os.chmod(output_shp_dir, 0o777)
            if (now_mexico.minute in {1,2,3} and now_mexico.hour != last_hour) or (len(os.listdir(output_shp_dir)) == 0):
                #descargar el shapefile de zonas de probabilidad de TC
                url = "https://www.nhc.noaa.gov/xgtwo/gtwo_shapefiles.zip"
                download_zip(url, output_shp_dir, 'zip')
                last_hour = now_mexico.hour
        except Exception as e:
            logging.error(
                "Error inesperado en la descarga de NOAA files: %s (%s). Reintentando en 60s.",
                str(e), e.__class__.__name__,
                exc_info=True
            )
            time.sleep(60) #espera para las excepciones


if __name__ == '__main__':
    main() 
