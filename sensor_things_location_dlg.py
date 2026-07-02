# -*- coding: utf-8 -*-
"""Module to show/identify a SensorThingsAPI Lacation.

Description
-----------

Libraries/Modules
-----------------
    
Notes
-----

- None.

Author
-------

- Creato da Sandro Moretti il 09/02/2022.
  2022 Dedagroup spa.

Members
-------
"""
import json

# Qgis\PyQt modules
from qgis.PyQt.QtCore import pyqtSlot, Qt, QUrl
from qgis.PyQt.QtGui import QColor
from qgis.PyQt import QtWidgets

from qgis.core import QgsWkbTypes, QgsProject, QgsMapLayer, QgsDataSourceUri
from qgis.gui import QgsGui, QgsRubberBand
from qgis.utils import iface

# plugin modules
from SensorThingsAPI import plgConfig, __QGIS_PLUGIN_NAME__ 
from SensorThingsAPI.log.logger import QgisLogger as logger
from SensorThingsAPI.html.generate import htmlUtil
from SensorThingsAPI.sensor_things_inspector_layer import SensorThingLayerUtils, SensorThingLoadDataTask
from SensorThingsAPI.sensor_things_osservazioni_dlg import SensorThingsObservationDialog
from SensorThingsAPI.sensor_things_browser import SensorThingsRequestError, WebEngineDialog


# 
#-----------------------------------------------------------
class SensorThingsLocationDialog(WebEngineDialog):
    """Dialog to show Location info"""
    
    def __init__(self, plugin, parent=None):
        """Constructor
        
        :param parent: 
        :type parent: QtWidgets
        """
        # init
        super().__init__(parent)
        QgsGui.enableAutoGeometryRestore(self)
        
        self.plugin = plugin
        self.page_data = {}
        self._lay_id = None
        self._feat_id = None
        self._fids = []
        self._rubberBand = None
        self._st_load_task = None
        self._st_load_tasks = []
        self._dataSourceUri = QgsDataSourceUri()
        
        self._osservazDlg = None
        
        # settings
        self.setWindowTitle(self.tr("Location"))
        
    def _get_observation_dialog(self):
        if self._osservazDlg is None:
            self._osservazDlg = SensorThingsObservationDialog(
                self.plugin, parent=iface.mainWindow()
            )
        return self._osservazDlg

    
    
    def closeEvent(self, _):
        """Close event method"""
        # reset
        self.page_data = {}
        logger.restoreOverrideCursor()
        
        # close Observations dialog
        if self._osservazDlg is not None:
            self._osservazDlg.close()
        
        # remove rubber band
        self._removeRubberBand()
        
        # cancel all active tasks
        SensorThingLoadDataTask.cancel_tasks(self._st_load_tasks)
        
    
    
    def show(self, layer, fid, fids):
        """Show a location info"""
        try:
            # init
            self._lay_id = layer.id()
            self._feat_id = fid
            self._fids = fids or []
            
            # remove rubber band
            self._removeRubberBand()
            
            # get feature
            feature = layer.getFeature(self._feat_id)
            if not feature:
                return
            
            # select feature
            layer.selectByIds([self._feat_id])
            
            # get feature location attribute
            location_id = SensorThingLayerUtils.getFeatureAttribute(feature, "id")
            location_name = SensorThingLayerUtils.getFeatureAttribute(feature, "name")
            location_desc = SensorThingLayerUtils.getFeatureAttribute(feature, "description")
            
            # show rubber band
            self._showRubberBand(layer, feature)
            
            # collect features info
            feats_info = []
            for fid in fids:
                feat = layer.getFeature(fid)
                if feat:
                    feats_info.append({
                        'fid': fid,
                        'locId': SensorThingLayerUtils.getFeatureAttribute(feat, "id"),
                        'locName': SensorThingLayerUtils.getFeatureAttribute(feat, "name"),
                        'lodDesc': SensorThingLayerUtils.getFeatureAttribute(feat, "description")
                    })
                    
            # hide Osservazioni dialog
            self._get_observation_dialog().hide()
            
            # show wait cursor
            logger.setOverrideCursor()
            
            # compose url
            provider = layer.dataProvider()
            self._dataSourceUri = provider.uri()
            service_url = QUrl(self._dataSourceUri.param('url')) ##QUrl(provider.dataSourceUri())
            if not service_url.isValid():
                raise ValueError("{}: {}".format(self.tr("Invalid layer URL"), service_url.toString()))
                
            # extract SensorThing element
            sta_entity = self._dataSourceUri.param('entity')
            
            if sta_entity not in ['Location', 'Datastream', 'MultiDatastream', 'FeatureOfInterest']:
                raise ValueError("{}: {}".format(self.tr("Invalid SensorThings entity"), sta_entity))
                
            # prepare data for HTM template
            self.page_data = {
                'locale': self.plugin.locale,
                'base_folder': htmlUtil.getBaseUrl(),
                'feature': {
                    'fid': self._feat_id,
                    'locId': location_id,
                    'locName': location_name,
                    'lodDesc': location_desc
                },
                'features': feats_info,
                'location': None,
                'things': None,
                'sta_entity': sta_entity
            }    
            
            if sta_entity == 'Location':
                self.setWindowTitle(self.tr("Location"))
            elif sta_entity == 'Datastream':
                self.setWindowTitle(self.tr("Datastream"))
            elif sta_entity == 'MultiDatastream':
                self.setWindowTitle(self.tr("MultiDatastream"))
            elif sta_entity == 'FeatureOfInterest':
                self.setWindowTitle(self.tr("Feature Of Interest"))
            
            # Request location data
            featureLimit = self.getLimit('featureLimit')
            
            url = SensorThingLayerUtils.getUrl(layer)
            
            self._st_load_task = self._create_load_task(
                url=url, entity=sta_entity, featureLimit=featureLimit,
                expandTo=None, sql="id eq {}".format(SensorThingLayerUtils.quoteValue(location_id)),
                prefix_attribs=None,
            )
            self._st_load_task.dataLoaded.connect(self._location_callback)
            self._st_load_task.get()
            
            # show spinner
            self._show_web_spinner(True)
            
        except SensorThingsRequestError as ex:
            logger.restoreOverrideCursor()
            self.logError(
                "{}: {}".format(self.tr("Entity dialog visualization"), str(ex)))
            
        except Exception as ex:
            logger.restoreOverrideCursor()
            self.logError(
                "{}: {}".format(self.tr("Entity dialog visualization"), str(ex)))
    
    
    
    def logError(self, message):
        """Log error message"""
        # hide spinner
        self._show_web_spinner(False)
        # log
        logger.msgbar(
            logger.Level.Critical, 
            str(message), 
            title=__QGIS_PLUGIN_NAME__,
            clear=True
        ) 
        logger.msgbox(
            logger.Level.Critical, 
            str(message),  
            title=__QGIS_PLUGIN_NAME__
        )
        
    
    
    def rejectRequest(self, message):
        """Show Observations dialog"""
        # hide spinner
        self._show_web_spinner(False)
        # restore cursor
        logger.restoreOverrideCursor()
        if message:
            self.logError(str(message))
        
    
    
    def _show_web_spinner(self, show):
        if show:
            self.runJavaScript("sensorThingsShowSpinner(true);")
        else:
            self.runJavaScript("sensorThingsShowSpinner(false);")
        
    
       
    def _show_callback(self):
        try:
            # check if got all data 
            if self.page_data.get('location') is None or\
               self.page_data.get('things') is None:
                self.rejectRequest(None)
                return
            
            logger.restoreOverrideCursor()
           
            # load HTL document 
            template_name = 'location.html'
            template = htmlUtil.generateTemplate(template_name)
            self.setHtml(template.render(self.page_data), htmlUtil.getBaseUrl())
        
            # show dialog 
            QtWidgets.QDialog.show(self)
           
        except Exception as ex:
            self.logError(
                "{}: {}".format(self.tr("Location dialog visualization"), str(ex)))
    
    
    
    def _location_callback(self, load_task: SensorThingLoadDataTask):
        try:
            # Check if data
            if load_task.exception:
                raise load_task.exception
            
            if load_task.error_message:
                self.rejectRequest(load_task.error_message)
                return
            
            if not self.page_data:
                self.rejectRequest(None)
                return
            
            # store data
            sta_entity = self.page_data['sta_entity'] or '' 
            
            loc_data = load_task.data[0] if len(load_task.data) > 0 else {}
            
            if sta_entity == 'Datastream' or sta_entity == 'MultiDatastream':
                loc_data['name'] = "{} {}".format(self.tr("Area observed by"), loc_data['Name'])
                loc_data['description'] = ''
            
            self.page_data['location'] = loc_data
            self.page_data['location']['url'] = load_task.getUrl()
            
            # Request things data
            featureLimit = self.getLimit('featureLimit')
            thingLimit = self.getLimit('thingLimit')
            
            if sta_entity == 'Location':
                expandTo = "Thing:limit={}".format(thingLimit)
                self._st_load_task = self._create_load_task(
                    url=load_task.getUrl(), entity='Location', featureLimit=featureLimit,
                    expandTo=expandTo, sql=load_task.getFilter(), prefix_attribs='Thing_',
                )
            
            elif sta_entity == 'FeatureOfInterest':
                observationLimit = self.getLimit('observationLimit')
                datastreamLimit = self.getLimit('datastreamLimit')
                expandTo = "Observation:limit={};Datastream:limit={};Thing:limit={}".format(observationLimit, datastreamLimit, thingLimit)
                
                self._st_load_task = self._create_load_task(
                    url=load_task.getUrl(), entity='FeatureOfInterest', featureLimit=featureLimit,
                    expandTo=expandTo, sql=load_task.getFilter(),
                    prefix_attribs='Observation_Datastream_Thing_',
                )
            
            elif sta_entity == 'Datastream' or sta_entity == 'MultiDatastream':
                self._st_load_task = self._create_load_task(
                    url=load_task.getUrl(), entity=sta_entity, featureLimit=featureLimit,
                    expandTo=expandTo, sql=load_task.getFilter(), prefix_attribs='Thing_',
                )
            
            else:
                raise ValueError("{}: {}".format(self.tr("Invalid SensorThings entity"), sta_entity))
            
            self._st_load_task.dataLoaded.connect(self._things_callback)
            self._st_load_task.get()
            
        except Exception as ex:
            self.logError(
                "{}: {}".format(self.tr("Entity dialog visualization"), str(ex)))
    
    
     
    def _things_callback(self, load_task: SensorThingLoadDataTask):
        try:
            # Check if data
            if load_task.exception:
                raise load_task.exception
            
            if load_task.error_message:
                self.rejectRequest(load_task.error_message)
                return
            
            if not self.page_data:
                self.rejectRequest(None)
                return
            
            # store data
            url = load_task.getUrl()
           
            self.page_data['things'] = list({d.get('@iot.id', '???'): d for d in (load_task.data or [])}.values())
            
            for thing in self.page_data['things']:
                thing['url'] = url
                thing['description'] = (thing['description'] or '').strip() or self.tr("No description")
            
            # try to show dialog
            self._show_callback()
           
        except Exception as ex:
            self.logError(
                "{}: {}".format(self.tr("Location dialog visualization"), str(ex)))
        
    
     
    def _showRubberBand(self, layer, feature):
        """Show rubber band in scene"""
        # remove previous rubber band
        self._removeRubberBand()
        
        try:
            # create rubber band
            canvas = iface.mapCanvas()
            geom = feature.geometry()
            geomType = geom.type()
            
            color = QColor("red")
            color.setAlphaF(0.78)
            fillColor = QColor(255, 71, 25, 150)
        
            self._rubberBand = QgsRubberBand(canvas, geomType)
            self._rubberBand.setColor(color)
            self._rubberBand.setFillColor(fillColor)
              
            if geomType == QgsWkbTypes.PointGeometry:
                cfg_styles = plgConfig.get_value('layer/styles', {})
                properties = cfg_styles.get('default', {})
                symbol_size = properties.get('pointRadius', 8)
                
                self._rubberBand.setWidth(symbol_size * 5)
                self._rubberBand.setIcon(QgsRubberBand.ICON_CIRCLE)
                self._rubberBand.addPoint(geom.asPoint(), True, 0, 0)
            else:
                self._rubberBand.addGeometry(geom, layer)
                self._rubberBand.setWidth(5)
                
            
            # show rubber band    
            self._rubberBand.show()
        except:
            pass
    
    
    
    def _removeRubberBand(self):
        """Remove rubber band from scene"""
        if self._rubberBand:
            canvas = iface.mapCanvas()
            canvas.scene().removeItem(self._rubberBand)
            self._rubberBand = None
    
    
    @pyqtSlot(str, result=str)
    def getThingData(self, thing_id):
        """Injected method to get thing data as JSON."""
        try:
            things_data = self.page_data.get('things', [])
            thing_data = next(
                (i for i in things_data if str(i.get('@iot.id')) == str(thing_id)),
                None,
            )
            if not thing_data:
                raise ValueError(self.tr("Invalid Thing ID"))
            return SensorThingLoadDataTask.page_data_to_json(thing_data)

        except Exception as ex:
            self.logError(str(ex))
            return '{}'

    @pyqtSlot(str, result=int)
    def getLimit(self, name):
        return self.plugin.main_panel.getLimit(name)
    
    @pyqtSlot(str, result=int)
    def getObservationLimit(self, name):
        return self.plugin.main_panel.getObservationLimit(name)
    
    @pyqtSlot(str, str)
    def loadObservationsData(self, ds_row_json, options_json):
        """Show the observations dialog (JSON args for Qt6 WebChannel)."""
        try:
            if not self.isVisible():
                return

            ds_row = json.loads(ds_row_json) if ds_row_json else {}
            options = json.loads(options_json) if options_json else {}

            self._get_observation_dialog().hide()
            date_filter = options.get('filterTime', '')
            query_params = options.get('queryParams', '')
            is_multidatastream = bool(options.get('isMultidatastream', False))

            self.page_data['selectRow'] = ds_row
            self.page_data['filterTime'] = date_filter
            self.page_data['queryParams'] = query_params
            self.page_data['isMultidataStream'] = is_multidatastream

            self._get_observation_dialog().show(self.page_data, self._dataSourceUri)

        except Exception as ex:
            self.logError(
                "{}: {}".format(self.tr("Loading Observations data"), str(ex)))
            
            
    @pyqtSlot(str)
    def changeLocation(self, str_fid):
        """Injected method to location in multi feature selection"""
        
        # init
        if self._lay_id is None or\
           self._feat_id is None:
            return
        
        fid = int(str_fid)
        
        # search layers in TOC
        root_node = QgsProject.instance().layerTreeRoot()
        tree_layer = root_node.findLayer(self._lay_id)
        if tree_layer:
            layer = tree_layer.layer()
            # check if vector layer
            if layer.type() == QgsMapLayer.VectorLayer:
                # show Location info
                self.show(layer, fid, self._fids)
       
            