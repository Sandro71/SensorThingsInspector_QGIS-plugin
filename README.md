## SensorThings Inspector plugin

The SensorThings Inspector plugin is an evolution of the old SensorThingsAPI Viewer plugin for QGIS and has been developed by Deda Next (www.dedanext.it) with the support of Faunalia (www.faunalia.eu) and BRGM (https://www.brgm.fr/en), the French Geological Survey.

The plugin enables QGIS (www.qgis.org, versions 3.384 onwards) to inspect time-series data provided by endpoints compliant with OGC SensorThings API standard protocol (https://www.ogc.org/standards/sensorthings).

This readme is a brief walkthrough on how to install and use the plugin in QGIS.
1.	Installation<br>The plugin can be downloaded from this repository as a zip file.<br>Once installed (as a local zip file), the user interface shows a simple menu and a toolbar with four commands:
•	Setup Upload 'SensorThings API' layer from remote server
•	Inspect Show location informationfeatures in layer
•	Export layer
Note: the following screenshots show the user interface in Italian.
  
immagine da sostituire con una aggiornata dopo la riorganizzazione di toolbar e menu.
In Italiano le voci saranno: Imposta il layer SensorThings, Ispeziona gli elementi del layer, Esporta il layer.
To test the plugin, the following endpoints can be configuredused:
•	https://iot.comune.fe.it/FROST-Server/v1.1/Locations 
(data about air quality, bike transits, traffic by Municipality of Ferrara, Italy)
•	https://airquality-frost.k8s.ilt-dmz.iosb.fraunhofer.de/v1.1/Locations 
(data about air quality from AQ stations inaround Europe, by Fraunhofer Institute, Germany)
•	https://demography.k8s.ilt-dmz.iosb.fraunhofer.de/v1.1/Locations 
(demographic statistics, by Fraunhofer Institute, Germany)
•	https://iot.hamburg.de/v1.1/Locations 
(fromby the City of Hamburg)
•	https://ogc-demo.k8s.ilt-dmz.iosb.fraunhofer.de/v1.1/Locations 
(water data by OGC)
•	http://covidsta.hft-stuttgart.de/server/v1.1/Locations 
(COVID data by HFT Stuttgart, Germany)
.O.. other public endpoints are also available here:
 at https://github.com/opengeospatial/sensorthings/blob/master/PublicEndPoints.md
2.	Setup
Clicking on the “Setup SensorThings layer” the Connect button the user can set:
•	the STA endpoint to connect to;
•	the structure of the SensorThings layer to be used as a basis for the inspection: 
the chosen structure has to include geometrical features (either Locations, FeaturesOfInterest or Multi/Datastreams) in order for the inspector tool to work;
•	the time extent limits to be used to inspect the time series of Observations; 
•	the layer style
•	the dynamic temporal control of the layer
	
	 to list all the locations available and optionally filter them using their own properties; select one or more items and clic the button Add (or double clic).
 
immagine da sostituire con una aggiornata che mostri il contenuto aggiornato del pannello del plugin dopo la riorganizzazione dei tab (magari mostrando screenshots di tutti e 4 i tabs?).
O... once the SensorThings layer is set selected the Locations to be added in the map, you will see something like this:
 
immagine da sostituire con una aggiornata.
3.	Feature inspection
3.	Tthe command "Show location informationInspect features in layer" button activates a tool opens a new popup window to query a single location; when the location feature is clicked on the map, the a popup window appears describing  with the list of related Datastreams and MultiDatastreams available(measured parameter) available:
 
4.	Time series inspection
4.	Bby clicking on one of  the icons placed in the observation column of the Multi/Datastreams table in the “features inspection” popup windowthe right-side button, the user can has the possibility to access to the corresponding timeseries  (Oobservations) for each parameter and visualizeget data in either tabular or chart formats, with the possibility to change modify the temporal extent of the subset currently shown.filter (dates from/to):

