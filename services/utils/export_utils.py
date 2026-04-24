import netCDF4 as nc
from html2image import Html2Image
import os
from datetime import datetime


def export_trajectory_netcdf(prob_traj, cluster_id, output_dir, timestamp):
    """
    Exports the calculated probable trajectory to a standard NetCDF file.
    Assumes prob_traj is a list of tuples: [(lon, lat, datetime, ...), ...]
    """
    if not prob_traj:
        return None

    nc_path = os.path.join(output_dir, f'hurakan_cluster_{cluster_id}_{timestamp}.nc')

    # Create dataset in write mode
    with nc.Dataset(nc_path, 'w', format='NETCDF4') as ds:
        # Global Attributes (Important metadata for users)
        ds.title = f"Probable Trajectory - Cluster {cluster_id}"
        ds.source = "Hurakan Platform - Ensemble Analysis"
        ds.history = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC"

        # Create dimensions
        num_points = len(prob_traj)
        ds.createDimension('time', num_points)

        # Create variables
        lats = ds.createVariable('lat', 'f4', ('time',))
        lats.units = 'degrees_north'

        lons = ds.createVariable('lon', 'f4', ('time',))
        lons.units = 'degrees_east'

        # Save time as hours since a base epoch
        times = ds.createVariable('time', 'f8', ('time',))
        base_date = prob_traj[0][2]  # Use the first point as epoch
        times.units = f"hours since {base_date.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        times.calendar = 'gregorian'

        # Extract data from the trajectory list
        lons_data = [pt[0] for pt in prob_traj]
        lats_data = [pt[1] for pt in prob_traj]

        # Calculate hours since the first point
        times_data = [(pt[2] - base_date).total_seconds() / 3600.0 for pt in prob_traj]

        # Assign data to variables
        lats[:] = lats_data
        lons[:] = lons_data
        times[:] = times_data

    return nc_path


def export_map_image(map_html_path, output_dir, timestamp):
    """
    Renders the generated Folium HTML map as a static PNG image.
    """
    try:
        # Initialize tool specifying the output folder
        hti = Html2Image(output_path=output_dir)
        hti.browser.flags = ['--disable-features=DBus', '--no-sandbox', '--disable-gpu']
        image_name = f'static_map_{timestamp}.png'

        # Define the virtual screen size for the screenshot
        hti.screenshot(
            html_file=map_html_path,
            save_as=image_name,
            size=(1920, 1080)  # Full HD resolution
        )
        image_path = os.path.join(output_dir, image_name)
        return image_path
    except Exception as e:
        print(f"Error generating map image: {e}")
        return None