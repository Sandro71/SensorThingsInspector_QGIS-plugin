# SensorThings Inspector plugin

The SensorThings Inspector plugin is an evolution of the old SensorThingsAPI Viewer plugin for QGIS and has been developed by Deda Next (www.dedanext.it) with the support of Faunalia (www.faunalia.eu) and BRGM (https://www.brgm.fr/en), the French Geological Survey.

The plugin enables QGIS (www.qgis.org, versions 3.384 onwards) to inspect time-series data provided by endpoints compliant with OGC SensorThings API standard protocol (https://www.ogc.org/standards/sensorthings).

This readme is a brief walkthrough on how to install and use the plugin in QGIS.

## 1. Installation<br>
The plugin can be downloaded from this repository as a zip file.<br>Once installed (as a local zip file), the user interface shows a simple menu and a toolbar with four commands:

- Setup 'SensorThings' layer
- Inspect features in layer
- Export layer

<br>

Note: the following screenshots show the user interface in Italian.

<p>
  <img width="200" src="https://github.com/user-attachments/assets/51e59d1f-5599-4c0e-90f9-49654107ff4c" />
  <br>
  <em>plugin menu</em>
</p>

<p>
  <img width="200" src="https://github.com/user-attachments/assets/4b8a5140-cc5b-4eb9-8329-35639ec5964c" />
  <br>
  <em>plugin toolbar</em>
</p>

<br>

To test the plugin, the following endpoints can be used:

- https://iot.comune.fe.it/FROST-Server/v1.1/Locations <br>(data about air quality, bike transits, traffic by Municipality of Ferrara, Italy)
- https://airquality-frost.k8s.ilt-dmz.iosb.fraunhofer.de/v1.1/Locations <br>(data about air quality from around Europe, by Fraunhofer Institute, Germany)
- https://demography.k8s.ilt-dmz.iosb.fraunhofer.de/v1.1/Locations <br>(demographic statistics, by Fraunhofer Institute, Germany)
- https://iot.hamburg.de/v1.1/Locations <br>(from the City of Hamburg)
- https://ogc-demo.k8s.ilt-dmz.iosb.fraunhofer.de/v1.1/Locations <br>(water data by OGC)
- http://covidsta.hft-stuttgart.de/server/v1.1/Locations <br>(COVID data by HFT Stuttgart, Germany)

Other public endpoints are also available here: <br>https://github.com/opengeospatial/sensorthings/blob/master/PublicEndPoints.md

## 2. Setup<br>
Clicking on the “Setup SensorThings layer” button the user can set:
- the STA endpoint to connect to;
- the structure of the SensorThings layer to be used as a basis for the inspection:<br>
  the chosen structure has to include geometrical features (either Locations, FeaturesOfInterest or Multi/Datastreams) in order for the inspector tool to work;
- the time extent limits to be used to inspect the time series of Observations; 
- the layer style
- the dynamic temporal control of the layer

<br>

<p>
  <img width="400" src="https://github.com/user-attachments/assets/dab0a133-7ce5-47d5-a63a-7759cce08c17" />
  <br>
  <em>Source</em>
</p>

<p>
  <img width="400" src="https://github.com/user-attachments/assets/4da99710-dc8c-4895-9d62-2fa61baf0508" />
  <br>
  <em>Style</em>
</p>

<p>
  <img width="400" src="https://github.com/user-attachments/assets/aff78258-d3a4-477b-83d0-8e9b33cef35c" />
  <br>
  <em>Temporal Analysis</em>
</p>

Once the SensorThings layer is set you will see something like this:
 
immagine da sostituire con una aggiornata.

## 3. Feature inspection<br>
The "Inspect" button activates a tool query a single location; when the feature is clicked on the map, a popup window appears describing the list of related Datastreams and MultiDatastreams available:

<img width="700" alt="Show location information" src="https://github.com/user-attachments/assets/e744f075-a903-4404-8eef-e03a74bfb712" />

## 4. Time series inspection<br>
By clicking on one of  the icons placed in the observation column of the Multi/Datastreams table in the “features inspection” popup window, the user can access to the corresponding timeseries (Observations) and visualize data in either tabular or chart formats, with the possibility to modify the temporal extent of the subset currently shown.

