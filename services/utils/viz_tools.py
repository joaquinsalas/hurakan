import os
import matplotlib.pyplot as plt
from matplotlib import dates as mdates

def apply_custom_style(fig, ax, style='dark'):
    """
    Applies a consistent theme to Matplotlib figures (2D and 3D).
    Optimized for both real-time analysis and historical evaluation.
    """
    bg_color = 'black' if style == 'dark' else 'white'
    fg_color = 'white' if style == 'dark' else 'black'

    fig.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    
    # Apply colors to labels and ticks for X and Y axes
    for axis in [ax.xaxis, ax.yaxis]:
        axis.label.set_color(fg_color)
        ax.tick_params(axis='both', colors=fg_color, labelsize=10)
    
    # Handling for 3D plots (useful for time-elevation-position analysis)
    if hasattr(ax, 'zaxis'): 
        ax.zaxis.label.set_color(fg_color)
        ax.tick_params(axis='z', colors=fg_color)
        ax.zaxis.set_major_formatter(mdates.DateFormatter('%m-%d %Hh'))

    # Style spines (borders)
    for spine in ax.spines.values():
        spine.set_color(fg_color)

    # Style legend if exists
    legend = ax.get_legend()
    if legend:
        frame = legend.get_frame()
        frame.set_facecolor(bg_color)
        frame.set_edgecolor(fg_color)
        for text in legend.get_texts():
            text.set_color(fg_color)

    ax.title.set_color(fg_color)
    ax.grid(True, linestyle='--', alpha=0.3, color=fg_color)
    
    return fig, ax

def save_plot(fig, output_path, dpi=300):
    """
    Saves figure ensuring the directory exists. 
    Ideal for saving RMSE plots in the evaluation workflow.
    """
    directory = os.path.dirname(output_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        
    fig.savefig(
        output_path, 
        dpi=dpi, 
        bbox_inches='tight', 
        facecolor=fig.get_facecolor()
    )
    plt.close(fig)

def get_category_color(category):
    """
    Returns the specific HEX color for hurricane categories.
    Used by both Folium (GeoJSON) and Matplotlib (Evaluation).
    """
    colors = {
        7: '#1745fc', # Tropical Depression
        8: '#0da0ba', # Tropical Storm
        1: '#fcd997', # Cat 1
        2: '#fabd4b', # Cat 2
        3: '#fa7d4b', # Cat 3
        4: '#fc6060', # Cat 4
        5: '#c67af5'  # Cat 5
    }
    return colors.get(category, '#808080') # Grey for unknown/low intensity