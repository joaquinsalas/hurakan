import os
import numpy as np
import logging
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform

# Internal modular imports
from services.utils.geo_math import haversine_vectorized
from services.utils.readers import parse_stitch_file

class ClusterEngine:
    """
    Core engine for Tropical Cyclone trajectory clustering.
    Uses strict temporal overlap logic to match original proven results.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def cluster_from_list(self, trajectories, distance_tol=200, min_size=10):
        """
        Calculates distance matrix and applies hierarchical clustering.
        Args:
            trajectories (list): List of trajectories (each a list of points).
            distance_tol (float): Linkage distance threshold in km.
            min_size (int): Minimum number of members to keep a cluster.
        """
        n_traj = len(trajectories)
        if n_traj < 2:
            return {'trajectories': trajectories, 'clusters': np.ones(n_traj, dtype=int)}

        # Build Distance Matrix
        dist_matrix = np.zeros((n_traj, n_traj))
        for i in range(n_traj):
            for j in range(i + 1, n_traj):
                traj_a = trajectories[i]['orig_traj'] if isinstance(trajectories[i], dict) else trajectories[i]
                traj_b = trajectories[j]['orig_traj'] if isinstance(trajectories[j], dict) else trajectories[j]
                dist = self._get_initial_point_distance(traj_a, traj_b)
                dist_matrix[i, j] = dist_matrix[j, i] = dist

        # Handle non-finite distances (trajectories that do not match criteria)
        finite_vals = dist_matrix[np.isfinite(dist_matrix)]
        fill_val = (np.max(finite_vals) * 2) if finite_vals.size > 0 else 1e6
        dist_matrix[~np.isfinite(dist_matrix)] = fill_val

        # Scipy Hierarchical Clustering (Single linkage as per original)
        condensed = squareform(dist_matrix)
        z_linkage = linkage(condensed, method='single')
        raw_clusters = fcluster(z_linkage, t=distance_tol, criterion='distance')

        # Filter clusters by size
        unique_lbls, counts = np.unique(raw_clusters, return_counts=True)
        valid_labels = unique_lbls[counts >= min_size]
        label_map = {old: new for new, old in enumerate(valid_labels, start=1)}

        final_traj, final_clusters = [], []
        for idx, traj in enumerate(trajectories):
            lbl = raw_clusters[idx]
            if lbl in label_map:
                final_traj.append(traj)
                final_clusters.append(label_map[lbl])

        return {
            'trajectories': final_traj, 
            'clusters': np.array(final_clusters)
        }

    def _get_initial_point_distance(self, traj_a, traj_b):
        """
        Calculates Haversine distance strictly between initial points (t0).
        Only valid if the initial times are within 12 hours (0.5 days) of each other.
        Replicates the logic of the legacy cluster_analysis.
        """
        if not (isinstance(traj_a, list) and isinstance(traj_b, list)):
            return np.inf

        # Filter valid points [lon, lat, datetime, ...]
        valid_a = [p for p in traj_a if isinstance(p, (list, tuple)) and len(p) >= 3]
        valid_b = [p for p in traj_b if isinstance(p, (list, tuple)) and len(p) >= 3]

        if not valid_a or not valid_b:
            return np.inf

        # 1. Determine initial timestamps
        t0_a = valid_a[0][2].timestamp()
        t0_b = valid_b[0][2].timestamp()

        # 2. Check within 12 hours (43200 seconds)
        if abs(t0_a - t0_b) <= 43200:
            # 3. Calculate vectorized Haversine distance
            lon_a, lat_a = valid_a[0][0], valid_a[0][1]
            lon_b, lat_b = valid_b[0][0], valid_b[0][1]
            
            # Using haversine_vectorized which supports scalars
            distance = haversine_vectorized(lon_a, lat_a, lon_b, lat_b)
            return float(distance)
        else:
            return np.inf

    def generate_3d_plot(self, results, output_fn, style='black'):
        """Generates 3D visualization of clusters with advanced styling."""
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D
        import matplotlib.dates as mdates

        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        trajs = results['trajectories']
        cl_ids = results['clusters']
        
        if not trajs: 
            print("No trajectories to plot.")
            return

        # Setup custom style from cluster_analysis
        if style == 'normal':
            bg_color, fg_color = 'white', 'black'
        else:
            bg_color, fg_color = 'black', 'white'

        fig.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)
        ax.xaxis.label.set_color(fg_color)
        ax.yaxis.label.set_color(fg_color)
        ax.zaxis.label.set_color(fg_color)
        ax.title.set_color(fg_color)
        ax.tick_params(axis='x', colors=fg_color)
        ax.tick_params(axis='y', colors=fg_color)
        ax.tick_params(axis='z', colors=fg_color)
        for spine in ax.spines.values():
            spine.set_edgecolor(fg_color)

        ax.set_xlabel(f'$longitude$', fontsize=20)
        ax.set_ylabel(f'$latitude$', fontsize=20)
        ax.set_zlabel(f'$time$', fontsize=14)
        ax.set_title(f'$trajectory clustering$', fontsize=20)
        ax.tick_params(axis='both', which='major', labelsize=14)
        ax.zaxis.set_major_formatter(mdates.DateFormatter('%m-%d %Hh'))

        n_clusters = np.max(cl_ids) if cl_ids.size > 0 else 1
        cmap = plt.cm.get_cmap('viridis', n_clusters)

        for k, traj in enumerate(trajs):
            cid = cl_ids[k]
            lons = [p[0] for p in traj]
            lats = [p[1] for p in traj]
            times = [mdates.date2num(p[2]) for p in traj]
            
            ax.plot(lons, lats, times, '-o', linewidth=0.8, markersize=2.5, 
                    markerfacecolor='none', markeredgewidth=0.8, 
                    color=cmap(cid-1), label=f"T{k:02d} (C{cid})")

        ax.xaxis.set_pane_color((0, 0, 0, 0))
        ax.yaxis.set_pane_color((0, 0, 0, 0))
        ax.zaxis.set_pane_color((0, 0, 0, 0))
        ax.grid(True, which='both', linestyle=':', linewidth=0.5)
        ax.view_init(elev=7, azim=-12)

        output_dir = os.path.dirname(output_fn)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        fig.savefig(output_fn, dpi=300, bbox_inches='tight', facecolor=bg_color)
        self.logger.info(f"3D cluster plot saved to {output_fn}")