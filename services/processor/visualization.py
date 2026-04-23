import os
import json
import glob
import numpy as np
import pandas as pd
import geopandas as gpd
import netCDF4
import folium
import matplotlib.dates as mdates
from collections import defaultdict
from folium import Element
from folium.features import DivIcon
from datetime import datetime, timezone
from dotenv import load_dotenv

from services.utils.config import logger

from services.utils.viz_tools import get_category_color

from services.utils.readers import (
    load_thresholds_csv,
    get_representative_date
)
from services.utils.geo_math import (
    get_saffir_category,
    calculate_bearing
)

from services.utils.export_utils import export_trajectory_netcdf, export_map_image
from services.utils.reporting import generate_csv_report, generate_pdf_report

# Processor Logic
from services.processor.processing import collect_trajectories_by_region
from services.processor.analysis import (
    filter_trajectory_outliers, 
    calculate_most_probable_trajectory,
    generate_uncertainty_cone, 
    smooth_lonlat_polygon,
    calculate_initial_cluster_dispersion
)

# AI Service Clients
from services.clusterer.cluster_engine import ClusterEngine
from services.classifier.classifier_request import run_ensemble_prediction

# Environment configuration
load_dotenv()
PROB_THR = float(os.getenv("HURAKAN_PROB_THR", "0.40"))
THRESHOLDS_CSV = os.getenv("THRESHOLDS_CSV")


def select_dynamic_thresholds(start_date, df_thresholds, base_dt=None):
    """
    Selects the distance tolerance and minimum cluster size
    based on the remaining lead time.
    """
    default_vals = {'link_tol_km': 300, 'min_n': 10}

    if df_thresholds is None or df_thresholds.empty:
        logger.warning("Thresholds DataFrame unavailable. Using default values.")
        return default_vals

    if not start_date:
        logger.warning("Could not estimate start date. Using default values.")
        return default_vals

    if base_dt is None:
        base_dt = datetime.now(timezone.utc)

    hours_to_start = (start_date - base_dt).total_seconds() / 3600.0
    logger.info(f"Calculated Lead Time: {hours_to_start:.2f} hours.")

    selected_row = None
    if hours_to_start < 0:
        selected_row = df_thresholds.iloc[-1]
    else:
        for _, row in df_thresholds.iterrows():
            if hours_to_start >= row['lead_time_hours']:
                selected_row = row
                break

        if selected_row is None:
            selected_row = df_thresholds.iloc[-1]

    return {
        'link_tol_km': int(selected_row['link_dist_threshold_km']),
        'min_n': int(selected_row['min_trajectories_per_cluster'])
    }

def build_segment_featurecollection(all_trajectories):
    """
    Builds the original GeoJSON structure for hurricane segments.
    """
    features = []
    for trk in all_trajectories:
        if len(trk) < 2: continue
        for i in range(len(trk) - 1):
            lon1, lat1, dt1, slp1, wind, elev1 = trk[i]
            cat_num = get_saffir_category(wind) if wind else 0
            features.append({
                "type": "Feature",
                "properties": {
                    "cat": f"C{cat_num}" if cat_num <= 5 else "TS" if cat_num == 8 else "TD",
                    "color": get_category_color(cat_num),
                    "wind_kmh": round(wind, 1) if wind else 'N/D',
                    "time": dt1.strftime("%Y-%m-%d %H:%M UTC"),
                    "slp_hPa": round(slp1, 1) if slp1 is not None else 'N/D'
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[lon1, lat1], [trk[i+1][0], trk[i+1][1]]]
                }
            })
    return {"type": "FeatureCollection", "features": features}

def generate_combined_map(timestamp, common_stitch_dir, output_dir):
    """
    Generates the interactive combined map with original HTML/JS timeline logic.
    """
    logger.info(f"--- Starting combined map generation for: {timestamp} ---")

    base_dt = datetime.strptime(timestamp, '%Y%m%d_%H').replace(tzinfo=timezone.utc)

    df_thresholds = load_thresholds_csv(THRESHOLDS_CSV)

    # 1. Collect trajectories
    trajs_pacific = collect_trajectories_by_region(common_stitch_dir, timestamp, 'pacifico')
    trajs_atlantic = collect_trajectories_by_region(common_stitch_dir, timestamp, 'atlantico')
    all_trajectories = trajs_pacific + trajs_atlantic

    if not all_trajectories:
        logger.warning("No trajectories found for combined map.")
        m = folium.Map(location=[23.6, -95], zoom_start=4, tiles="CartoDB positron")
        m.save(os.path.join(output_dir, f'map_{timestamp}.html'))
        return True

    # 2. Base map setup
    m = folium.Map(location=[23.6, -95], zoom_start=4, tiles="CartoDB positron")

    try:
        # Define la ruta a la carpeta donde guardarás los shapefiles
        shapefile_dir = os.path.join(os.getcwd(), 'data', 'assets', 'shapefiles')

        # Cargar Pacífico
        pacifico_shp = os.path.join(shapefile_dir, 'pacifico_shp_grande.shp')  # Asegúrate que el archivo se llame así
        if os.path.exists(pacifico_shp):
            gdf_pacifico = gpd.read_file(pacifico_shp)
            folium.GeoJson(
                gdf_pacifico,
                name="Limites Pacífico",
                style_function=lambda x: {
                    'color': '#D0D0D0',
                    'weight': 2,
                    'opacity': 1.5,
                    'fill':False
                }
            ).add_to(m)

        # Cargar Atlántico
        atlantico_shp = os.path.join(shapefile_dir, 'atlantico_shp_grande.shp')  # Asegúrate que el archivo se llame así
        if os.path.exists(atlantico_shp):
            gdf_atlantico = gpd.read_file(atlantico_shp)
            folium.GeoJson(
                gdf_atlantico,
                name="Limit Atlántico",
                style_function=lambda x: {
                    'color': '#D0D0D0',
                    'weight': 2,
                    'opacity': 1.5,
                    'fill': False
                }
            ).add_to(m)

    except Exception as e:
        logger.error(f"Error al cargar las regiones de análisis: {e}", exc_info=True)

    # 3. Locate original .nc file for metadata
    nc_file_path = None
    try:
        data_dir = os.path.join(os.getcwd(), 'data', 'raw_nc')
        search_patterns = [
            os.path.join(data_dir, 'pacifico', f"*{timestamp}*.nc"),
            os.path.join(data_dir, 'atlantico', f"*{timestamp}*.nc")
        ]
        for pattern in search_patterns:
            found = glob.glob(pattern)
            if found:
                nc_file_path = found[0]
                break
    except Exception as e:
        logger.error(f"Error searching for .nc metadata: {e}")

    # 4. Spaghetti Feature Group
    fg_spaghetti = folium.FeatureGroup(name="All Trajectories (Spaghetti)", show=True)
    fc_spaghetti = build_segment_featurecollection(all_trajectories)
    
    folium.GeoJson(
        data=fc_spaghetti,
        style_function=lambda x: {'color': x['properties']['color'], 'weight': 1, 'opacity': 0.6},
        tooltip=folium.GeoJsonTooltip(
            fields=['time', 'wind_kmh', 'cat', 'slp_hPa'],
            aliases=['Date:', 'Wind (km/h):', 'Category:', 'Pressure (hPa):'],
            style="background-color: #F0EFEF; border: 2px solid black; border-radius: 3px; box-shadow: 3px;"
        ),
        highlight_function=lambda x: {'weight': 3, 'opacity': 1.0}
    ).add_to(fg_spaghetti)

    # Markers for Start and End of each member
    for trk in all_trajectories:
        if not trk: continue
        # Start (Green)
        start_icon = DivIcon(icon_size=(14,14), icon_anchor=(7,7),
                             html='<div style="width:10px; height:10px; background-color:green; border-radius:50%; border:2px solid darkgreen;"></div>')
        folium.Marker(location=[trk[0][1], trk[0][0]], icon=start_icon,
                      popup=f"<b>Start:</b><br>{trk[0][2].strftime('%d-%b %H:%M')}").add_to(fg_spaghetti)
        # End (Grey)
        if len(trk) > 1:
            end_icon = DivIcon(icon_size=(14,14), icon_anchor=(7,7),
                               html='<div style="width:10px; height:10px; background-color:grey; border-radius:50%; border:2px solid black;"></div>')
            folium.Marker(location=[trk[-1][1], trk[-1][0]], icon=end_icon,
                          popup=f"<b>End:</b><br>{trk[-1][2].strftime('%d-%b %H:%M')}").add_to(fg_spaghetti)

    fg_spaghetti.add_to(m)
    spaghetti_jsvar = fg_spaghetti.get_name()

    # 5. Cluster Analysis
    palette = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#ffff33', '#a65628', '#f781bf']
    global_cluster_id = 0
    clusters_by_time = defaultdict(list)
    cluster_engine = ClusterEngine()

    regions_to_process = [('pacifico', trajs_pacific), ('atlantico', trajs_atlantic)]

    start_date = get_representative_date(all_trajectories)
    selected_thresholds = select_dynamic_thresholds(start_date, df_thresholds, base_dt)

    logger.info(
        f"Dynamically selected thresholds: Dist={selected_thresholds['link_tol_km']}km, MinN={selected_thresholds['min_n']}")

    cluster_data_for_export = []
    for region_name, region_trajs in regions_to_process:
        if not region_trajs: continue

        clustering_input = [{'fileID': idx, 'orig_traj': traj, 't': np.array(mdates.date2num([pt[2] for pt in traj])),
                             'lat': np.array([pt[1] for pt in traj]), 'lon': np.array([pt[0] for pt in traj])}
                            for idx, traj in enumerate(region_trajs)]

        clust_res = cluster_engine.cluster_from_list(
            clustering_input,
            distance_tol=selected_thresholds['link_tol_km'],
            min_size=selected_thresholds['min_n'],
        )

        trajs_by_cluster = defaultdict(list)
        if 'clusters' in clust_res and clust_res['clusters'] is not None:
            for traj_dict, lbl in zip(clust_res['trajectories'], clust_res['clusters']):
                if lbl != -1: trajs_by_cluster[lbl].append(traj_dict['orig_traj'])

        for local_lbl, traj_list in trajs_by_cluster.items():
            cluster_color = palette[global_cluster_id % len(palette)]
            filtered_list = filter_trajectory_outliers(traj_list, std_dev_threshold=2.0)
            if not filtered_list: continue

            estimated_date = get_representative_date(filtered_list)
            if not estimated_date: continue
            time_key = estimated_date.strftime('%Y-%m-%d %H:00')

            # Layer Cluster
            fg_cluster = folium.FeatureGroup(name=f"Cluster {global_cluster_id} ({region_name})", show=False)
            fc_c = build_segment_featurecollection(filtered_list)
            folium.GeoJson(data=fc_c, style_function=lambda x, c=cluster_color: {'color': c, 'weight': 1.5, 'opacity': 0.7}).add_to(fg_cluster)
            clusters_by_time[time_key].append({'layer': fg_cluster, 'jsvar': fg_cluster.get_name()})

            # AI Analysis (Classifier API)
            disp_km, _ = calculate_initial_cluster_dispersion(filtered_list)
            lead_h = (estimated_date - base_dt).total_seconds() / 3600
            features = {
                "n_trayectorias_best_cluster": [len(filtered_list)],
                "dispersion_km_best_cluster": [disp_km],
                "horas_diff_estimadas": [lead_h]
            }
            
            prob, pred = run_ensemble_prediction(features) #Get probability and predicted category from classifier

            if prob >= PROB_THR: 
                probable_track = calculate_most_probable_trajectory(filtered_list)
                if probable_track:
                    export_trajectory_netcdf(probable_track, global_cluster_id, output_dir, timestamp)
                    fg_prob = folium.FeatureGroup(name=f"Cluster {global_cluster_id} - Probable", show=False)
                    coords_prob = [[lat, lon] for lon, lat, _ in probable_track]
                    folium.PolyLine(locations=coords_prob, color="black", weight=4, opacity=0.9, dash_array='5,5').add_to(fg_prob)
                    
                    # Probable start marker
                    folium.CircleMarker(location=coords_prob[0], radius=6, color='darkgreen', fill=True, fill_color='lime').add_to(fg_prob)
                    
                    # Bearing Arrow
                    bearing = calculate_bearing(coords_prob[-2][0], coords_prob[-2][1], coords_prob[-1][0], coords_prob[-1][1])
                    icon_html = f'<div style="font-size: 20pt; color: black; transform: rotate({bearing-90}deg);">▶</div>'
                    folium.Marker(location=coords_prob[-1], icon=DivIcon(icon_size=(30,30), icon_anchor=(15,15), html=icon_html)).add_to(fg_prob)

                    # Uncertainty Cone
                    cone_coords = generate_uncertainty_cone(filtered_list, probable_track, [pt[2] for pt in probable_track])
                    if cone_coords is not None:
                        smooth_cone = smooth_lonlat_polygon(cone_coords)
                        folium.Polygon(locations=[(la, lo) for lo, la in smooth_cone], color=cluster_color, fill=True, fill_opacity=0.25).add_to(fg_prob)
                    
                    clusters_by_time[time_key].append({'layer': fg_prob, 'jsvar': fg_prob.get_name()})

            cluster_data_for_export.append({
                'cluster_id': global_cluster_id,
                'region': region_name,
                'n_trajectories': len(filtered_list),
                'dispersion_km': round(disp_km, 2) if isinstance(disp_km, (int, float)) else disp_km,
                'is_mature': bool(prob >= PROB_THR),
                'estimated_date': estimated_date.strftime('%Y-%m-%d %H:%M UTC') if estimated_date else 'Unknown'
            })
            global_cluster_id += 1

    # Add all generated layers to map
    for tkey, items in clusters_by_time.items():
        for item in items: item['layer'].add_to(m)

    initial_date_str = base_dt.strftime('%Y-%m-%d %H:%M UTC')
    if nc_file_path and os.path.exists(nc_file_path):
        try:
            with netCDF4.Dataset(nc_file_path, "r") as ds:
                tv = ds.variables["time"]
                fechas = netCDF4.num2date(tv[:], units=tv.units)
                if fechas.size > 0: initial_date_str = fechas[0].strftime('%Y-%m-%d %H:%M UTC')
        except Exception as e:
            logger.error(f"Error reading time from netCDF metadata {nc_file_path}: {e}", exc_info=True)

    # 7. Original HTML Elements (Legend & Logos)
    legend_html = f"""
        <div style="position: fixed; bottom: 40px; left: 10px; width: 180px; background-color: rgba(255, 255, 255, 0.85);
                    border:1px solid grey; border-radius: 5px; z-index:9999; font-size:12px; padding: 5px;">
        <b>Saffir-Simpson Category (km/h)</b><br>
        <span style="background-color: {get_category_color(5)}; display:inline-block; width:15px; margin-right:3px;">&nbsp;</span> C5 (&ge;252)<br>
        <span style="background-color: {get_category_color(4)}; display:inline-block; width:15px; margin-right:3px;">&nbsp;</span> C4 (209-251)<br>
        <span style="background-color: {get_category_color(3)}; display:inline-block; width:15px; margin-right:3px;">&nbsp;</span> C3 (178-208)<br>
        <span style="background-color: {get_category_color(2)}; display:inline-block; width:15px; margin-right:3px;">&nbsp;</span> C2 (154-177)<br>
        <span style="background-color: {get_category_color(1)}; display:inline-block; width:15px; margin-right:3px;">&nbsp;</span> C1 (119-153)<br>
        <span style="background-color: {get_category_color(8)}; display:inline-block; width:15px; margin-right:3px;">&nbsp;</span> TT (63-118)<br>
        <span style="background-color: {get_category_color(7)}; display:inline-block; width:15px; margin-right:3px;">&nbsp;</span> DT (&le;62)<br>
        <hr style="margin: 3px 0;">
        <div style="font-size: 10px;">{initial_date_str}</div>
        </div>"""
    m.get_root().html.add_child(Element(legend_html))

    logos_html = """
        <div style="position: fixed; bottom: 10px; right: 10px; z-index:9999; background-color: rgba(255, 255, 255, 0.7); padding: 5px; border-radius: 5px;">
          <a href="https://www.cicata.ipn.mx" target="_blank">
            <img src="https://1000marcas.net/wp-content/uploads/2022/01/IPN-Logo.png" style="height: 40px; margin: 5px;">
          </a>
        </div>"""
    m.get_root().html.add_child(Element(logos_html))

    # 8. Graticule and Scale JS
    graticule_js = f"""
       <script>
           window.addEventListener("load", function() {{
               var map = window["{m.get_name()}"];
               if (typeof map === "undefined") return;
               var script = document.createElement("script");
               script.src = "https://yaelhuerta1.github.io/leaftlet_graticule/leaflet.latlng-graticule.js";
               script.onload = function() {{
                   L.latlngGraticule({{showLabel: true, color: '#aaaaaa', weight: 0.8, font: '12px Verdana'}}).addTo(map);
                   L.control.scale({{imperial: false}}).addTo(map);
               }};
               document.head.appendChild(script);
           }});
       </script>
    """
    m.get_root().html.add_child(Element(graticule_js))

    # 9. Timeline Controller (Original HTML/JS)
    js_vars = {t: [item['jsvar'] for item in items] for t, items in clusters_by_time.items()}
    js_vars_str = json.dumps(js_vars, ensure_ascii=False)
    time_keys = sorted(js_vars.keys())

    buttons_html = ""
    if all_trajectories:
        buttons_html += '<button class="timeline-btn active" onclick="showSpaghetti(this)">Spaghetti</button>'
        for tkey in time_keys:
            hour_label = datetime.strptime(tkey, '%Y-%m-%d %H:%M').strftime('%d-%b %H')
            buttons_html += f"<button class=\"timeline-btn\" onclick=\"showLayersForTime(this, '{tkey}')\">{hour_label}</button>"

    date_chip = f'<span class="timeline-date">{initial_date_str}</span>'
    buttons_html = date_chip + buttons_html

    timeline_control_html = f"""
    <style>
      .timeline-container {{ position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); z-index: 1000;
        background-color: rgba(255,255,255,0.9); border: 1px solid #ccc; border-radius: 5px; padding: 8px;
        display: flex; gap: 5px; flex-wrap: wrap; max-width: 92vw; box-shadow: 0 1px 5px rgba(0,0,0,0.4); }}
      .timeline-btn {{ background: #fff; border: 1px solid #aaa; border-radius: 4px; padding: 5px 10px; cursor: pointer; font-size: 12px; }}
      .timeline-btn:hover {{ background: #f0f0f0; }}
      .timeline-btn.active {{ background: #3388ff; color: #fff; border-color: #3388ff; }}
      .timeline-date {{ display: inline-flex; align-items: center; padding: 5px 10px; font-size: 12px;
        background: #f4f6f9; border: 1px solid #d7dee9; color:#333; border-radius: 16px; pointer-events: none; user-select: none; }}
    </style>
    <div class="timeline-container">{buttons_html}</div>
    <script>
      const clustersByTimeVars = {js_vars_str};
      const allVarNames = Array.from(new Set(Object.values(clustersByTimeVars).flat()));
      const spaghettiVar = "{spaghetti_jsvar}";
      function getMap() {{ return window["{m.get_name()}"]; }}
      function showSpaghetti(btn) {{
        document.querySelectorAll('.timeline-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const map = getMap();
        if (!map) return;
        allVarNames.forEach(vn => {{ const lyr = window[vn]; if (lyr && map.hasLayer(lyr)) map.removeLayer(lyr); }});
        if (spaghettiVar) {{ const sp = window[spaghettiVar]; if (sp && !map.hasLayer(sp)) map.addLayer(sp); }}
      }}
      function showLayersForTime(btn, timeKey) {{
        document.querySelectorAll('.timeline-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const map = getMap();
        if (!map) return;
        const varsToShow = clustersByTimeVars[timeKey] || [];
        if (spaghettiVar) {{ const sp = window[spaghettiVar]; if (sp && map.hasLayer(sp)) map.removeLayer(sp); }}
        allVarNames.forEach(vn => {{ const lyr = window[vn]; if (lyr && map.hasLayer(lyr)) map.removeLayer(lyr); }});
        varsToShow.forEach(vn => {{ const lyr = window[vn]; if (lyr) map.addLayer(lyr); }});
      }}
      window.addEventListener('load', () => {{
        const firstBtn = document.querySelector('.timeline-btn');
        if (firstBtn) showSpaghetti(firstBtn);
      }});
    </script>
    """
    m.get_root().html.add_child(Element(timeline_control_html))

    combined_map_path = os.path.join(output_dir, f'map_{timestamp}.html')
    m.save(combined_map_path)
    logger.info(f"Combined map generated successfully at: {combined_map_path}")

    # --- EXPORT BLOCK ---
    logger.info("Initiating export to usable formats...")
    export_map_image(combined_map_path, output_dir, timestamp)
    if cluster_data_for_export:
        generate_csv_report(cluster_data_for_export, output_dir, timestamp)
        generate_pdf_report(cluster_data_for_export, output_dir, timestamp, combined_map_path)

    return True