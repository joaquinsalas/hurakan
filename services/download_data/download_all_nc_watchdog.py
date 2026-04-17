# Este programa esta hecho para ser usado en el flujo de trabajo del watchdog

#cada 6 horas ejecuta la descarga de la imagen más reciente y la guarda en una carpeta
#primero descarga el pacífico y cuando termina descarga el atlántico
# El script termina y no se sigue ejecutando



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
from requests.exceptions import ConnectionError
from googleapiclient.errors import HttpError
import zipfile

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dask.distributed import Client, LocalCluster #multiprocesamiento

from config import txt_time_dir, token_file, credentials_file, pacific_polygon, atlantic_polygon, EARTHENGINE_TOKEN, log_file, datasets_dir, app_dir #rutas
from config import variables # vars meteorologicas desde WN
from config import project_name #google cloud project
from config import SCOPES, timezone #otros

# Excepciones específicas #########################################################################
class IncompleteBlockError(Exception):
    """No hay 250 imágenes en el bloque aún."""
    pass

#definición de métodos ##########################|##################################################
#Autentica con la API de Google Drive usando OAuth2.
def authenticate_drive():
    auth_fail_count = 0
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
                    creds = flow.run_local_server(port=0)

                #guarda el token para futuras ejecuciones
                with open(token_file, 'w') as token: 
                    token.write(creds.to_json())

            logging.info("Autentificado en Google Drive.")
            return creds
        
        # Manejo de excepciones
        except (HttpError, ConnectionError) as e:
            auth_fail_count += 1
            logging.warning(
                "Falló la autenticación con Google Drive debido a un error de red o servicio externo: %s (%s). "
                "Verifica tu conexión o si el servicio de Google está accesible. Reintentando en 60s.",
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
                "Revisar stack trace para más detalles. Reintentando en 10s.",
                str(e), e.__class__.__name__,
                exc_info=True
            )
            time.sleep(10)

def initialize_GEE():
    while True:
        try: 
            ee.Initialize(project=project_name)
            logging.info(f"EarthEngine inicializado para el proyecto: {project_name}")
            break
        except socket.gaierror as e:
            logging.error("Sin conexión a Internet al inicializar EE: %s (%s). Reintentando en 60s.", e, e.__class__.__name__, exc_info=True)
        except EEException as e:
            logging.error("Error de Earth Engine al inicializar (%s): %s. Reintentando en 60s.", e.__class__.__name__, str(e), exc_info=True)
        except Exception as e:
            logging.error("Excepción inesperada durante EE.Initialize: %s (%s). Reintentando en 60s.", str(e), e.__class__.__name__, exc_info=True)
        # Esperar 1 min antes de reintentar la inicialización
        time.sleep(60)

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
        resp = service.files().list(q=q, spaces='drive', fields='files(id,name)').execute()
        files = resp.get('files', [])
        if not files:
            logging.debug(f"No se encontró ninguna carpeta llamada '{name}'")
        else:
            # toma la primera coincidencia
            folder = files[0]
            ids[name] = folder['id']
            logging.debug(f"Encontrada carpeta '{name}' → ID: {folder['id']}")
            
    return ids

def download_file(service, file_id, file_name, save_path):
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(os.path.join(save_path, file_name), 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        logging.debug(f"    → {file_name}: {int(status.progress() * 100)}%")
    fh.close()

def secuencia_descarga_drive(aux_dir, FOLDER_NAMES, service):
    # Revisa si las carpetas ya existen en el drive
    folder_ids = {}
    while len(folder_ids) != len(FOLDER_NAMES):
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
            resp = service.files().list(q=q, spaces='drive',
                                        fields='files(id,name)').execute()
            files = resp.get('files', [])

            if files:
                f = files[0]
                logging.info(f"Archivo detectado en '{name}': {f['name']}. Descargando...")
                download_file(service, f['id'], f['name'], aux_dir)
                # opcional: borrar el archivo remoto
                service.files().delete(fileId=f['id']).execute()
                downloaded.add(name)

        if len(downloaded) < len(folder_ids):
            logging.debug("Esperando 60s a que las task terminen y que los archivos esten disponibles en drive")
            time.sleep(60)

def check_files_before_download(task_names, aux_dir, FOLDER_NAMES, service):
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
        secuencia_descarga_drive(aux_dir, FOLDER_NAMES, service)

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
        logging.error(
            "Error de Earth Engine al intentar exportar imagen a Drive: %s (%s). "
            "Revisar parámetros de exportación o cuotas de uso.",
            str(e), e.__class__.__name__,
            exc_info=True
        )
        raise 
    except Exception as e:
        logging.error(
            "Error inesperado en get_surface_elevation(): %s (%s)",
            str(e), e.__class__.__name__,
            exc_info=True
        )
        raise

#guarda el tiempo en que tardó descargarse cada archivo en la ultima linea de un txt
def log_time(segundos, archivo_nc, ruta):
    # Crea la carpeta si no existe
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    # si el txt no existe, lo crea con la cabecera
    if not os.path.exists(txt_time_dir):
        with open(txt_time_dir, 'w') as f:
            f.write("filename,download_time_mins\n")
        logging.info(f"Archivo creado: {txt_time_dir}")

    archivo_name = archivo_nc.split('/')[-1] 
    with open(ruta, "a") as f:  # 'a' agrega la linea al final del archivo
        f.write(f"{archivo_name},{segundos/60} mins\n")

def export_forecast_block_to_drive(now_mexico, region_roi, zona, FOLDER_NAMES):
    #define el rango de horas de pronóstico para cada bloque
    forecast_ranges = [[0, 60], [72, 120], [132, 180], [192, 240], [252, 300], [312, 360]]
    task_names = []

    try: 
        for i in range(len(forecast_ranges)):
            init_date_utc = define_date(now_mexico)
            logging.debug(f"Exportando bloque {i} desde {forecast_ranges[i][0]}h hasta {forecast_ranges[i][1]}h")

            dataset = (
                ee.ImageCollection("projects/gcp-public-data-weathernext/assets/126478713_1_0")
                .filter(ee.Filter.date(init_date_utc))
                .filter(ee.Filter.gte('forecast_hour', forecast_ranges[i][0]))
                .filter(ee.Filter.lte('forecast_hour', forecast_ranges[i][1]))
                .select(list(variables.keys()))
            )

            num_images = dataset.size().getInfo()
            if num_images != 250: # Cada bloque debe de tener 250 imágenes cada uno para poder continuar
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
        logging.error(
            "Error de Earth Engine al intentar exportar imagen a Drive: %s (%s). "
            "Revisar parámetros de exportación o cuotas de uso.",
            str(e), e.__class__.__name__,
            exc_info=True
        )
        raise 
    except IncompleteBlockError:
        raise
    except Exception as e:
        logging.error(
            "Error inesperado en export_forecast_block_to_drive(): %s (%s)",
            str(e), e.__class__.__name__,
            exc_info=True
        )
        raise

def convert_forecast_tifs_to_netcdf(tif_files, output_netcdf):
    #ejemplo de una band name "202505070000_202505071200_0_mean_sea_level_pressure"
    """
    Convierte TIFs exportados por Earth Engine a un único NetCDF con estructura específica:
    time x lat x lon, con variables meteorológicas y elevación opcional.
    
    Args:
        tif_files (list): Lista de archivos .tif por bloques.
        output_netcdf (str): Ruta al archivo .nc de salida.
    """
    
    if not tif_files:
        raise ValueError("La lista de archivos .tif está vacía. Nada que convertir.")
    
    # declaración de varaibles
    var_name_map = {
        'mean_sea_level_pressure': 'mslp',
        '10m_u_component_of_wind': 'u10',
        '10m_v_component_of_wind': 'v10',
        '300_geopotential': 'geopotential_300',
        '500_geopotential': 'geopotential_500'
    }
    expected_vars = list(var_name_map.values())
    # Expresión regular para extraer la fecha del forecast y nombre de la vaariable:
    band_regex = re.compile(
        r'(\d{12})_(\d{12})_\d+_'
        r'(mean_sea_level_pressure|10m_u_component_of_wind|'
        r'10m_v_component_of_wind|300_geopotential|500_geopotential)'
    )

    # Iniciar Dask con paralelización en 10 hilos
    cluster = LocalCluster(n_workers=10, threads_per_worker=1, dashboard_address=None)
    client = Client(cluster)

    # Para cada variable guardaremos una lista de DataArrays (cada DataArray = un forecast en 2D lat×lon)
    data_arrays = {var: [] for var in expected_vars}
    time_hours = []      # Lista con todos los "forecast_hr" en horas desde 1970
    lat_vals = None
    lon_vals = None

    try: 
        # Procesar cada TIF (en paralelo, lazy)
        for tif_path in tif_files:
            logging.debug(f"Leyendo {tif_path}")
            da = rxr.open_rasterio(
                tif_path,
                masked=True,
                chunks={"band": 50, "y": 256, "x": 256}
            )
            da = da.rename({'band': 'band', 'y': 'lat', 'x': 'lon'})

            # Invertir latitud si está al revés
            if da.lat.values[0] < da.lat.values[-1]:
                da = da.sel(lat=da.lat[::-1])

            # Extraer el nombre de la variable del archivo TIF
            try:
                band_names = list(da.descriptions)
            except Exception:
                # Si no existe da.descriptions, tiramos mano de attrs
                bm = da.attrs.get("long_name", da.attrs.get("description", None))
                if isinstance(bm, (list, tuple)):
                    band_names = list(bm)
                else:
                    # Si no hay nombres de banda no podemos convertir a nc
                    raise ValueError(
                        f"El tif no tiene nombres de bandas en 'descriptions' ni 'attrs'. Intentar volver a descargar"
                    )

            # Para cada banda dentro de este TIF extrae variable y forecast_hr
            # Guardar la capa 2D (lat×lon) en data_arrays[var]
            for idx in range(da.sizes["band"]):
                raw_name = band_names[idx]
                m = band_regex.search(raw_name)
                if not m:
                    # Si no coincide con el patrón, se salta
                    continue

                date_str_12 = m.group(2)   # ej. "202505070000"
                var_raw    = m.group(3)    # ej. "mean_sea_level_pressure"
                var_short  = var_name_map[var_raw]

                # Convertimos ese string a datetime y luego a "horas desde 1970"
                dt = datetime.strptime(date_str_12, "%Y%m%d%H%M")
                epoch = datetime(1970, 1, 1)
                delta = dt - epoch
                forecast_hr = int(delta.total_seconds() // 3600)

                # Obtén lazy chunk de la banda idx (2D: lat×lon)
                layer_2d = da.isel(band=idx)
                layer_2d.attrs.clear() # limpia todos los attrs heredados

                # Guardamos el DataArray (lazy) en la lista correspondiente
                data_arrays[var_short].append(layer_2d)

                # Solo una vez por cada forecast_hr (la primera variable que se procese para esa hora)
                # Para no duplicar timestamps en time_hours (todas las variables comparten la misma hora)
                if var_short == "mslp": 
                    time_hours.append(forecast_hr)

                # Guardamos coords lat/lon una única vez:
                if lat_vals is None:
                    lat_vals = da.lat.values
                    lon_vals = da.lon.values

        # Construir el Dataset
        ds = xr.Dataset(
            coords={
                "time": ("time", np.array(time_hours, dtype=int)),
                "lat":  ("lat",  lat_vals),
                "lon":  ("lon",  lon_vals)
            }
        )
        ds["time"].attrs["units"] = "hours since 1970-01-01 00:00:00"
        ds["time"].attrs["calendar"] = "proleptic_gregorian"

        # Para cada variable, stackeamos las listas de DataArray (cada uno lazy) en un solo arreglo (time, lat, lon)
        for var_short in expected_vars:
            if not data_arrays[var_short]:
                # En caso de que en algún tif no haya aparecido esa variable, saltamos
                continue

            # Con xarray.concat unimos por dimensión “time”
            da_concat = xr.concat(data_arrays[var_short], dim="band")  # ahora band=tiempo
            da_concat = da_concat.rename({"band": "time"})

            # Asegurarnos de que la dimensión “time” tenga la misma longitud que ds.coords["time"]
            da_concat["time"] = ds["time"]

            # Añadimos al dataset
            ds[var_short] = da_concat
            ds[var_short].attrs["_FillValue"] = np.nan

        # Borra la variable "spatial_ref" si existe, y limpia el grid_mapping de las variables
        if "spatial_ref" in ds:
            ds = ds.drop_vars("spatial_ref")
        target_vars = expected_vars[:]
        for v in target_vars:
            if v in ds and "grid_mapping" in ds[v].attrs:
                ds[v].attrs.pop("grid_mapping")

        ds.to_netcdf(output_netcdf)
        logging.info(f"Guardado Weather Next NetCDF en {output_netcdf}")

    except Exception as e:
        logging.error(
            "Error inesperado en convert_forecast_tifs_to_netcdf: %s (%s)",
            str(e), e.__class__.__name__,
            exc_info=True
        )
        raise  #reintentar descargar los archivos desde el inicio
    finally:
        # Cerremos el cluster de Dask para liberar recursos
        client.close()
        cluster.close()

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
        response = service.files().list(
            q="mimeType='application/vnd.google-apps.folder' and name contains 'EarthEngineForecasts_' and trashed = false",
            spaces='drive',
            fields="files(id, name)"
        ).execute()

        folders = response.get('files', [])
        if not folders:
            logging.debug("No se encontraron carpetas que coincidan con el patrón.")
        else:
            for folder in folders:
                name = folder['name']
                fid = folder['id']

                if pattern.match(name):
                    try:
                        service.files().delete(fileId=fid).execute()
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
            "Error al listar carpetas de Google Drive para eliminación: %s (%s)",
            str(e), e.__class__.__name__,
            exc_info=True
        )


    logging.info("Vaciando papelera de Google Drive...")
    try:
        while True:
            # Listar archivos en la papelera
            response = service.files().list(
                q="trashed = true",
                spaces='drive',
                fields="nextPageToken, files(id, name)"
            ).execute()

            files = response.get('files', [])
            if not files:
                break
            for file in files:
                try:
                    service.files().delete(fileId=file['id']).execute()
                except HttpError as e:
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
            "Error al intentar listar o procesar archivos en la papelera de Google Drive: %s (%s). "
            "No se pudieron recuperar o eliminar elementos. Revisar la conexión o permisos.",
            str(error), error.__class__.__name__,
            exc_info=True
        )

def borrar_archivos(output_dir, aux_dir, inicio, txt_time_dir, service, output_file):
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
    log_time(duracion, output_file, txt_time_dir)

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

# main ##########################################################################################
def main():
    # Setup logging (solo se escribirán los logs de INFO en adelante)
    logging.basicConfig(filename='/mnt/HurricaneAPI/cenapred_NextWeather/code/download_data/borrame.log', level=logging.INFO,
                        format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    logging.info('================================================================================================\n' + "Iniciando script de descarga de datos de Weather Next")


    #declaración de variables
    standar_time_zone = pytz.timezone(timezone)
    FOLDER_NAMES = []

    # Initialize Google Earth Engine (reintenta si no hay conexión)
    #os.environ['EARTHENGINE_TOKEN'] = EARTHENGINE_TOKEN
    initialize_GEE()
    # #autentificar en google drive
    creds = authenticate_drive()
    service = build('drive', 'v3', credentials=creds)

    finish_download = 0 # Contador de descargas finalizadas
    horarios_permitidos = {0, 6, 12, 18}
    while finish_download < 2:
        # Obtener la hora actual en la zona horaria de México
        now_mexico = datetime.now(standar_time_zone)
        ultimo_horario = max([h for h in horarios_permitidos if h <= now_mexico.hour])
        now_mexico = now_mexico.replace(hour=ultimo_horario, minute=0, second=0, microsecond=0)
        #now_mexico = now_mexico.replace(hour=12, minute=0, second=0, microsecond=0)
        # crear el nombre de archivo si está dentro del horario permitido
        fecha_string = now_mexico.strftime('%Y%m%d_%H')

        # Busca los archivos de cada zona
        zonas = ['pacifico', 'atlantico']
        for zona in zonas:
            # Definir directorios dependiendo de la zona
            aux_dir = f'{app_dir}auxiliary_files_{zona}/'
            output_dir = f'{datasets_dir}downloaded_nc_{zona}/'
            output_file = f'{output_dir}regional_weathernext_{fecha_string}_{zona}.nc' #el archivo final
            # Crea los directorios si no existen
            os.makedirs(os.path.dirname(aux_dir), exist_ok=True)
            os.makedirs(os.path.dirname(output_dir), exist_ok=True)

            # si el archivo más reciente no existe, busca que esté disponible para descargar
            if not os.path.exists(output_file):
                try:
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
                    check_files_before_download(task_names, aux_dir, FOLDER_NAMES, service)
                    #########################################################################

                    #agregar la ruta de los archivos a la lista de tareas (menos el de surface_elevation)
                    task_names = [os.path.join(aux_dir, name) for name in task_names]
                    task_names = [t for t in task_names if 'surface_elevation' not in os.path.basename(t)]

                    #convertir el par de tiff en un solo netcdf
                    nc_file_WN = f'{aux_dir}regional_weathernext_{fecha_string}.nc'
                    convert_forecast_tifs_to_netcdf(task_names, nc_file_WN)

                    # a este nc agregarle la elevation
                    add_elevation(nc_file_WN, f'{aux_dir}surface_elevation_{fecha_string}_{zona}.tif', output_file)

                    #eliminación de archivos temporales y calculo del tiempo
                    borrar_archivos(output_dir, aux_dir, inicio, txt_time_dir, service, output_file)

                    finish_download += 1
                    logging.info(f"Descarga de {output_file} finalizada.")

                except IncompleteBlockError:
                    logging.debug(
                        "Bloque incompleto: No son 250 imágenes."
                    )
                except Exception as e:
                    logging.error(
                        "Error inesperado: %s (%s)",
                        str(e), e.__class__.__name__,
                        exc_info=True
                    )
                    finish_download = 0
            else:
                logging.debug(f"El archivo {output_file} ya existe, no es necesario descargar.")
                finish_download += 1
        # Esperar 60 segundos antes de revisar nuevamente
        time.sleep(60)
    logging.info("Descargas de nc terminadas")

    #descargar el shapefile de zonas de probabilidad de TC
    url = "https://www.nhc.noaa.gov/xgtwo/gtwo_shapefiles.zip"
    output_shp_dir = f"{datasets_dir}NOAA_files"
    download_zip(url, output_shp_dir, 'zip')

if __name__ == '__main__':
    main() 