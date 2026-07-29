# System User's Manual


The Hurakán system facilitates the detection, monitoring, and forecasting of tropical cyclones through the visualization and analysis of potential meteorological phenomena, using detailed current information about variables such as temperature, pressure, humidity, and wind conditions in basins of interest and their temporal predicted evolution. The main objective is to increase awarness about potential tropical cyclones that could affect living conditions in coastal areas. The information entered into the system consists of meteorological forecasted information of the basins of interest at a certain resolution (0.25 degrees) obtained from the Google Earth Engine collection WeatherNext 2 [[1]](#reference-1), which is updated every six hours. This information is available year-round, so it can be used any day of the year. In the present version of the Hurakán system, the basins of interest include the Northeastern Pacific and the North Atlantic, both close to the coastal areas of Mexico in the Pacific and Atlantic Oceans, as shown in  Figure 1. Historically, hurrican season runs between May 15 and November 30 for the former and from June 1 to November 30 for the latter, with the highest incidence between August and September.

## Table of Contents
- [Requirements](#requirements)
- [Accessing Hurakán](#accessing)
- [Interface Description](#interface)
- [Available Information and Context Window](#available)
- [Activities](#activities)
- [Examples of Forecasting](#examples)
- [References](#references)
  

<img src="../figures/01ROI.PNG"  alt="The two basins of interest: the Eastern Pacific and the North Atlantic"/>
Figure 1. The defined regions of interest include Northeastern Pacific (blue) and the North Atlantic (green) basins.  





## Requirements<a name = "requirements"></a>
To properly visualize the possible trajectories and their cones of uncertainty for the probabilistic atmospheric data, the following are required:
- A web server with the Hurakán platform (see [Installation Manual](../README.md) ) posting at specific URL.
- A client web browser with Javascript enabled (Google Chrome 146, Safari 17, Microsoft Edge 145, or Mozilla Firefox 148 are recommended).
- System access credentials (the Hurakán system administrator can provide these credentials; see [Accessing Hurakán](#accessing)).



## Accessing Hurakán<a name = "accessing"></a>
Suppose the web server platform posts at URL https://hurakan.cicataqro.ipn.mx . In the **address bar** of the web browser write off `https://hurakan.cicataqro.ipn.mx` and press `<enter>`

List of possible URL to access services in Hurakán
- `https://hurakan.cicataqro.ipn.mx` - Initial access or `login` window
- `https://hurakan.cicataqro.ipn.mx/login` - `login` window
- `https://hurakan.cicataqro.ipn.mx/logout` - `logout` window
- `https://hurakan.cicataqro.ipn.mx/health` - `status` window


Hurakán mantains controlled access because of the metereological information and their possible consecuences. The adminstrator must give, for each person, a user name and password.
When accesing the initial window or the `login` window, the person must input their credentials in each input field, as shown in the Figure 2(a).
After login, the next window will show the map for the data available and will allow interaction with the system.
When finish using Hurakán, the web browser can be closed or type in the browser address bar `https://hurakan.cicataqro.ipn.mx/logout`. A window will pop out and show what is illustred in Figure 2(b).


|  *(a) Login screen* |  *(b) Logout screen* |
| :---: | :---: |
| <img src="../figures/02hurakan_login_2.png" alt="Hurakán login screen" width="420"> | <img src="../figures/03hurakan_logout_2.png" alt="Hurakán logout screen" width="420"> |

Figure 2. Login/Logout window. Credentials are provided by the system administrator.




## Interface description<a name = "interface"></a>

Given the probabilistic nature of its data, the Hurakán system generates possible tropical cyclone trajectories within a time window of up to 15 days for up to 50 different atmospheric scenarios with a lead time of 6 hours. The Spaghetti drawing in Figure 5 shows an example of such a visualization for Genevieve, a tropical storm formed on July 24, 2026, and still active as a hurricane by July 29.  The interface includes the following elements (see Figure 4):

- World Map. It identifies the global position of trajectories, with a resolution of 10m to 1000km, allowing for precise trajectory tracking. The map center can be moved, and from there, zoom in (up to 10m) or zoom out (up to 1000km).
- Saffir-Simpson Category Box. Displays the color associated with different wind speeds. Each color distinguishes between *DT* (TD, tropical depression), *TT* (TS, tropical storm), *Ci* (hurricane categories 1, ..., 5) and provide their velocity ranges in km/h.
- Central Panel. This panel provides the current WeatherNext 2 data being processsed in Coordinate Universal Time (UTC) standard. The central part of Mexico is UTC-6, now that the country does not shift times during Spring and Autum. It also includes a *Spaghetti* button, which can toggle to show the identified trajectories and the most probable overall trajectory for a tropical cyclone that has been deemed as strong or stronger than a tropical storm. In addition, it includes date buttons for each possible trajectory cluster that has been deemed mature enough to be classified as a tropical storm or stronger. The trajectories show the forecasted Saffir-Simpson scale colors, the starting and ending points of that trajectory, and information at the ending point. Note that the velocity of winds correspond to the average over a cell with a 0.25 degrees resolution. Therefore, the wind speed may be a conservative estimate respect to the strongest wind gust that may be observed.
- Zoom Controls. The map view can be zoomed in or out by using either the free-wheel in some mouses or by clicking on the +/-  symbols at the upper-left corner of the screen. Note that the zoom range extends from 10 m to 1000 km.
- Map Scale. The current scale of the map is given by the horizontal width of the rectangle in the bottom-left corner of the window, just below the Saffir-Simpson Category box. 
- Spaghetti: The identified trajectories are shown, indicating the probable speed through it, its probable starting and ending points given the specific date. To facilitate visualization, a trajectory can be selected at its ending point (green at the start and a dark gray point at the end). For an event occurring in a certain date, the possible trajectories can be displayed turning on and off the Spaghetti botton. The default will show the spaghetties.  The latter occurs just in certain cases, basically when a cluster and classification analysis determine that an ensemble of trajectories are in a position to describe a tropical storm.  Note that each of the 50 atmospheric scenarios may contain an indetermined number of trajectories.
- Cone of Uncertainty. If the Spaghetti boton is turned on, there will be a Cone of Uncertainty, the most likely trajectory and its band of uncertainty with two standard deviations by side. This  occurs in any event when an ensemble of trajectories form a structure mature enough to be as strong or stronger than a tropical storm. In such a case, there is a prediction about a tropical cyclone having a certain trajectory. Given the trajectories for a timestamp, an area with wide equal to two standard deviations is shown spreading along the forecasted trajectory.

<img src="../figures/04window_elements.png" alt="Scale selected" />

Figure 4. Tropical Cyclone Genevieve. Example of the interactive hurakán system map. Given WeatherNext 2 atmospheric forecasted scenarios for a date, such as July 29, 2026, the estimated trajectories for an up to 15-day period are shown. Each trajectory corresponds to the forecasted evolution of a different atmospheric scenario. Each trajectory shows the storm's speed on a given  date in color, corresponding to the Saffir-Simpson Hurricane Wind Scale on the legend box in the bottom-left.


## Activities<a name = "activities"></a>
In the Hurakán system, given the available information, the following activities can be performed:
- Date selection. If there is a tropical cyclone that has been deemed as strong or stronger than a tropical storm, there will be one or more dates to choose from.  Select the date of the data to be reviewed and then toggle between Spaghetti and most likely trajectory with cone of uncertainty.


<img src="../figures/hurakan_spaguetti.png" alt="spaghetti button" />
Figure 6. The Spaghetti button shows/occults the data group by individual forecast trajectories for the 50 atmospheric scenarios. Sometimes there aren't data to show, it depends on the metereological data from de day selected.

  - Spaghetti: The identified trajectories are shown, indicating the probable speed of the meteor, its probable starting and ending points given the specific date. To facilitate visualization, a trajectory can be selected at its ending point, and the date information at that point will be displayed. Figure 4 and Figure 5 illustrate the Spaghetti and the Cone of Uncertainty versions.

<img src="../figures/hurakan_spaguetti_info.png" alt="spaghetti info" />
Figure 7. Spaghetti info for each possible trajectory. The info is shown at the initial and ending point of the tarjectory.

  
    
<img src="../figures/hurakan_trajectory.png" alt="Date possible trajectory and cone of uncertainty" />
Figure 8. Overall possible trajectory for the date selected. The button(s) with the date(s) can shown a forecast of the trajectory ending in the date displayed.

<img src="../figures/hurakan_scale.png" alt="Scale selected" />
Figure 9. The size of the scale in the map is shown in the bottom-left corner, below the Saffir-Simpson scale.

- Interactive visualization. On the map, the central point can be moved by right-clicking on the mouse and dragging the mouse icon around the screen. Simiarly, the view can be zoomed in or out by using either the free-wheel in some mouses or by clicking on the +/-  symbols at the upper-left corner of the screen. Note that the zoom range extends from 10 m to 1000 km. The current scale of the map is given by the horizontal width of the rectangle in the bottom-left corner of th window, just below the Saffir-Simpson Category box.



<img src="../figures/hurakan_zoomin.png" alt="Button zoom in" />
Figure 10. The size of the scale in the map (shown as the horizontal length of the box at the bottom-left corner) can be reduced/increased with the `Zoom in`/`Zoom out` button at the top-right corner with the `+`/`-` sign or the mouse wheel.  




## Examples of detection and tracking<a name = "examples"></a>

In this section, several cases are analyzed to demonstrate hurricane capabilities. To identify tropical cyclones, the nomenclature used by NOAA and NHC for the genesis of a tropical cyclone is employed, indicating the year (YYYY), the day of the year (DDD), the hemisphere (N or S), the latitude in degrees (LLL), and the longitude in degrees (HHH); the name assigned to the storm is also used.

### Tropical Cyclone 2023294N09264 (Otis)
<img src="../figures/otis_app.PNG" alt="20231001 Tropical Cyclone Lidia" />
Figure 11. 20231001 Tropical Cyclone Otis.

- Category 5 hurricane (SSHWS)
- Duration: October 22 – October 25
- Peak intensity: 165 mph (270 km/h) (1-min); 922 mbar (hPa) [from Wikipedia](https://en.wikipedia.org/wiki/Hurricane_Otis)

### Tropical Cyclone Lidia
<img src="../figures/lidia_app.PNG" alt="20231003 Tropical Cyclone Lidia" />
Figure 12. 20231003 Tropical Cyclone Lidia.

- Category 4 hurricane (SSHWS)
- Duration: October 3 – October 11
- Peak intensity: 140 mph (220 km/h) (1-min); 942 mbar (hPa) [from Wikipedia](https://en.wikipedia.org/wiki/Hurricane_Lidia_(2023))




## References<a name = "references"></a>
<a id="reference-1">[1]</a> Ferran Alet and Ilan Price and Andrew El-Kadi and Dominic Masters and Stratis Markou and Tom R. Andersson and Jacklynn Stott and Remi Lam and Matthew Willson and Alvaro Sanchez-Gonzalez and Peter W. Battaglia (2025). *Skillful joint probabilistic weather forecasting from marginals*. Nature. [Link to Paper](https://arxiv.org/abs/2506.10772)



