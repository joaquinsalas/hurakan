# descarga el último shapefile de huracanes de NOAA
#cada 6 horas se va a estar descargando el zip
#este scrips no se ejecuta en el servidor, es un script separado que sepuede adaptar mostrar lsa zonas de probabilidad decargadas en el mapa

import requests
import zipfile
import os
import geopandas as gpd
import folium
import glob
import shutil



def safe_tooltip_fields(gdf):
    return [col for col in gdf.columns if col != "geometry" and gdf[col].notnull().any()]

def show_map(files_dir, save_html_path):
    # Leer shapefiles
    gdf_areas = gpd.read_file(glob.glob(os.path.join(files_dir, "gtwo_areas_*.shp"))[0])
    gdf_lines = gpd.read_file(glob.glob(os.path.join(files_dir, "gtwo_lines_*.shp"))[0])
    gdf_points = gpd.read_file(glob.glob(os.path.join(files_dir, "gtwo_points_*.shp"))[0])

    # Crear mapa centrado en el Pacífico mexicano
    m = folium.Map(location=[15.0, -105.0], zoom_start=4, tiles="cartodb positron")

    # Añadir áreas (relleno naranja rayado)
    folium.GeoJson(
        gdf_areas,
        name="Áreas",
        style_function=lambda x: {
            'fillColor': 'orange',
            'color': 'orange',
            'weight': 2,
            'fillOpacity': 0.4,
            'dashArray': '5, 5'
        },
        tooltip=folium.GeoJsonTooltip(fields=safe_tooltip_fields(gdf_areas))
    ).add_to(m)

    # Añadir líneas (trayectorias)
    folium.GeoJson(
        gdf_lines,
        name="Trayectoria estimada",
        style_function=lambda x: {
            'color': 'red',
            'weight': 2
        },
        tooltip=folium.GeoJsonTooltip(fields=safe_tooltip_fields(gdf_lines))
    ).add_to(m)

    # Añadir puntos (posiciones del ciclón)
    for _, row in gdf_points.iterrows():
        folium.Marker(
            location=[row.geometry.y, row.geometry.x],
            icon=folium.Icon(icon="glyphicon glyphicon-remove", prefix='glyphicon', color='orange'),
            tooltip=str(row)
        ).add_to(m)

    # Añadir capas y guardar
    folium.LayerControl().add_to(m)
    m.save(save_html_path)

#descarga un archivo mediante un url, si es zip lo descomprime
def download_zip(url, output_dir, type):
    # Crear directorio si no existe
    try:
        # Crear el directorio (y borrar todo si ya existe)
        if os.path.exists(output_dir):
            for filename in os.listdir(output_dir):
                file_path = os.path.join(output_dir, filename)
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
        else:
            os.makedirs(output_dir)
        os.chmod(output_dir, 0o777)

        filename = url.split("/")[-1]
        zip_path=f'{output_dir}/{filename}'

        # Descargar el archivo
        response = requests.get(url, timeout=20)
        if response.status_code != 200:
            print("No se pudo descargar el archivo shp de zonas de probabilidad de TC")
            """logging.error(
                "No se pudo descargar el archivo shp de zonas de probabilidad de TC",
                str(e), e.__class__.__name__,
                exc_info=True
            )"""
            return
        with open(zip_path, "wb") as f: #con éxito
            f.write(response.content)
        print("Archivo descargado exitosamente.")

        # descomprime si es zip
        if type == 'zip': 
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(output_dir)
                os.remove(zip_path)
            except zipfile.BadZipFile: # zip corrupto
                print("El archivo zip está corrupto o no es un zip válido.")
                """logging.error(
                    "El archivo zip está corrupto o no es un zip válido.",
                    str(e), e.__class__.__name__,
                    exc_info=True
                )"""
                return
        
        # Dar permisos 777 a todos los archivos extraídos
        for root, dirs, files in os.walk(output_dir):
            for name in files:
                os.chmod(os.path.join(root, name), 0o777)
            for name in dirs:
                os.chmod(os.path.join(root, name), 0o777)
    
    except requests.exceptions.RequestException as e:
        print('Error de red al descargar shp de zonas de probabilidad de TC')
        """logging.error(
            "Error de red al descargar shp de zonas de probabilidad de TC",
            str(e), e.__class__.__name__,
            exc_info=True
        )"""
    except Exception as e:
        print('Error inesperado al descargar shp de zonas de probabilidad de TC')
        """logging.error(
            "Error inesperado al descargar shp de zonas de probabilidad de TC",
            str(e), e.__class__.__name__,
            exc_info=True
        )    """     
    


# main ##############################################
#descarga los shp con las zonas de probabilidad de ciclones tropicales de NOAA
url = "https://www.nhc.noaa.gov/xgtwo/gtwo_shapefiles.zip"
output_shp_dir = "/home/nathaliealvarez/NathalieAlvarez/Huracanes/local_Hurikan/HurricaneData/NOAA_files"
download_zip(url, output_shp_dir, 'zip')

#crea el mapa donde se ven las áreas con sus probabilidades
save_html_path = "/home/nathaliealvarez/NathalieAlvarez/Huracanes/local_Hurikan/HurricaneData/output_maps/mapa_areas.html"
show_map(output_shp_dir, save_html_path)
 