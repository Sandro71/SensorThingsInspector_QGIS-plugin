# -*- coding: utf-8 -*-
"""SensorThingsAPI 2 main panel

Description
-----------

Utility class for the plugin configuration.

Libraries/Modules
-----------------

- None.
    
Notes
-----

- None.

Author(s)
---------

- Created by Sandro Moretti on 09/02/2022.
  Dedagroup Spa.

Members
-------
"""

import os
import re

from PyQt5.QtGui import QStandardItem
from PyQt5.QtCore import Qt, QEvent, QMetaType
from PyQt5.QtWidgets import QWidget, QDockWidget

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.core import Qgis, QgsProject, QgsApplication, QgsProviderRegistry, QgsVectorLayer, QgsStyle
from qgis.gui import (QgsGui,
                      QgsRendererPropertiesDialog,
                      QgsAbstractDataSourceWidget,
                      QgsVectorLayerTemporalPropertiesWidget)
from qgis.utils import iface

from SensorThingsAPI_2 import __QGIS_PLUGIN_NAME__, plgConfig
from SensorThingsAPI_2.log.logger import QgisLogger as logger
from SensorThingsAPI_2.utils.widget import QtWidgetUtils 
from SensorThingsAPI_2.utils.layer_utils import LayerUtils 
from SensorThingsAPI_2.sensor_things_api_layer import __SENSORTHINGS_PROVIDER_NAME__, SensorThingLayerUtils

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/sensor_things_api_main_panel.ui'))


class StRendererPropertiesDialog(QgsRendererPropertiesDialog):
    
    def __init__(self, layer: QgsVectorLayer, style: QgsStyle, embedded: bool, parent: QWidget):
        """Constructor"""
        super().__init__(layer, style, embedded, parent)
        
    def rendererChanged(self):
        """Called when user changes renderer type"""
        super().rendererChanged()
    

class SensorThingsApiMainPanel(QtWidgets.QDockWidget, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super().__init__(parent)
        
        self.source_selector = None
        self.style_dlg = None
        
        self.updating = False
        self.st_layer_id = ''
        self.st_style_widget = None
        self.st_style_dialog = None
        self.st_temporal_settings_widget = None
        
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
 
        #####################################################################
        # Create source data selector for SensorThings provider
        registry = QgsProviderRegistry.instance()
        if __SENSORTHINGS_PROVIDER_NAME__ not in registry.providerList():
            #TODO: exception
            pass
            
        self.source_selector = QgsGui.sourceSelectProviderRegistry().createSelectionWidget(
            __SENSORTHINGS_PROVIDER_NAME__, self, Qt.Widget, 0)
            
        if self.source_selector is None:
            #TODO: exception
            pass
            
        buttonBox = self.source_selector.findChild(QtWidgets.QDialogButtonBox)
        if buttonBox is not None:
            closeButton = buttonBox.button(QtWidgets.QDialogButtonBox.Close)
            if closeButton is not None:
                closeButton.setEnabled(False)
        
        self.source_selector.setMapCanvas( iface.mapCanvas() )	
        
        self.source_selector.addVectorLayer.connect( self.onAddVectorLayer )
                    
        self.tabSourceSelector.layout().insertWidget(0, self.source_selector)
        
        self.source_selector.installEventFilter(self)
        
        #####################################################################
        # Style
        self.btnStyleReload.clicked.connect(self.onStyleReload)
        
        self.btnStyleApply.setEnabled(False)
        self.btnStyleApply.clicked.connect(self.onStyleApply)
        
        self.lblNoStyle.setText("")
        
        self.pnlStyle.setEnabled(False)
        
        ####################################################################
        # Analysis
        self.gbxSpatial.collapsedStateChanged.connect(self.OnAnSpatialCollapse)
        
        self.gbxTemporal.collapsedStateChanged.connect(self.OnAnTemporalCollapse)
        
        self.gbxObservProperty.collapsedStateChanged.connect(self.OnAnObservPropertyCollapse)
        
        self.cmbObservProperty.checkedItemsChanged.connect(self.OnAnObservPropertyChecked)
        
        self.gbxSpatial.setVisible(False)
        self.gbxObservProperty.setVisible(False)
        self.gbxOptions.setVisible(False)
        self.gbxTemporal.setVisible(True)
        
        self.btnLocationIdentify.setToolTip(self.tr("Show location information"))
        
        self.btnToolExport.setToolTip(self.tr("Export layer to file..."))
        self.btnToolExport.clicked.connect(self.onExportClicked)
        
        self.btnAnalysisApply.clicked.connect(self.onAnalysisApply)
        
        #####################################################################
        # Define export
        self.btnExport.clicked.connect(self.onExportClicked)
        
        #####################################################################
        # Define TAB widget
        self.tabControl.setTabVisible(self.tabControl.indexOf(self.tabExport), False)
        
        themeName = QgsApplication.themeName()
        if re.search("Night", themeName, re.IGNORECASE) or re.search("Dark", themeName, re.IGNORECASE):
            self.tabControl.setStyleSheet("QTabBar::tab:selected { background-color: rgb(0, 0, 25); }")
        else:
            self.tabControl.setStyleSheet("QTabBar::tab:selected { background-color: rgb(121, 215, 255); }")
        
        #####################################################################
        # Start
        self.layerSetting = {}
        
        iface.mapCanvas().renderComplete.connect( self.onRenderComplete )
        
        layer = iface.activeLayer()
        
        self.setLayer(layer)
    
    
    def onRenderComplete(self,  painter):
        """On Map Canvas render complete"""
        logger.restoreOverrideCursor()
        
        
        
    def onAddVectorLayer(self, vectorLayerPath: str, layerName: str, providerKey: str):
        """Adds a vector layer to the current project"""
        # Set wait cursor
        logger.setOverrideCursor(Qt.WaitCursor)
        
        _ = iface.addVectorLayer(vectorLayerPath, layerName, providerKey)
        
  
    def onStyleWidgetChanged(self):
        """Slot for style definition changing"""
        self.btnStyleApply.setEnabled(True)
        
        
    def onStyleReload(self):
        """Reload current layer style"""
        self.setLayer(self.getLayer())
        
        
    def onStyleApply(self):
        """Apply layer style changes"""
        
        try:
            # Check if valid layer
            if self.getLayer() is None:
                return
            
            # Check if style widget is None
            if self.st_style_dialog is None:
                return
            
            # Apply  style
            logger.setOverrideCursor(Qt.WaitCursor)
               
            LayerUtils.set_visibility([self.getLayer()], show=True)
                
            self.st_style_dialog.apply()
            
            self.btnStyleApply.setEnabled(False)
            
            self.getLayer().triggerRepaint()
            
        finally:
            pass
    
    
    def OnAnSpatialCollapse(self, collapsed: bool):
        """ """
        laySettings = self.getLayerSettings()
        
        laySettings['Analysis']['Spatial']['Collapsed'] = collapsed
        
    def OnAnTemporalCollapse(self, collapsed: bool):
        """ """
        laySettings = self.getLayerSettings()
        
        laySettings['Analysis']['Temporal']['Collapsed'] = collapsed
        
    def OnAnObservPropertyCollapse(self, collapsed: bool):
        """ """
        laySettings = self.getLayerSettings()
        
        laySettings['Analysis']['ObservProperty']['Collapsed'] = collapsed
        
    def OnAnObservPropertyChecked(self, items):
        """ """
        laySettings = self.getLayerSettings()
        
        if not laySettings['Analysis']['ObservProperty']['Data']:
            return
        
        laySettings['Analysis']['ObservProperty']['CheckedItems'] = items
        
        
    def onAnalysisApply(self):
        """Apply analysis changes"""
        
        # Init
        layer = self.getLayer()
        if layer is None:
            return
        
        # Save temporal settings to layer
        if self.st_temporal_settings_widget is not None:
            self.st_temporal_settings_widget.saveTemporalProperties()
            
            self.showTemporalControlWidget(layer.temporalProperties().isActive())
                
            LayerUtils.updateLayerInToc(layer)
    
    def onExportClicked(self):
        """Export layer"""
        
        if self.getLayer() is None:
            return
        
        output_formats = plgConfig.get_value("export/output_formats", [])
         
        LayerUtils.saveAsVectorFile(self.getLayer(), onlySelected=False, defaultToAddToMap=True, output_formats= output_formats)
        
    
    
     
    def getLayerInitSetting(self):
        """Return layer panel initial settings"""
        return {
            'Analysis': {
                'Spatial': {
                    'Collapsed': False
                },
                'Temporal': {
                    'Collapsed': False
                },
                'ObservProperty': {
                    'Collapsed': False,
                    'Data': {},
                    'CheckedItems': []
                }
            }
        }
            
    
    def getLayerSettings(self):
        """Return current panel layer settings"""
        return self.layerSetting.get(self.st_layer_id, self.getLayerInitSetting())
    
    def getLayer(self):
        """Returns layer instance"""
        layer = QgsProject.instance().mapLayer(self.st_layer_id) if self.st_layer_id  else None
        
        return layer
    
    def setLayer(self, layer):
        """Set layer instance to widget"""
        
        # Init
        wd_layer = self.getLayer()
        
        if layer != wd_layer: 
            # reset previous layer instance
            if wd_layer is not None:
                try:
                    wd_layer.styleChanged.disconnect(self.updateStylePanel)
                except:
                    pass
                
                try:
                    wd_layer.temporalProperties().changed.disconnect(self.updateAnTemporalPanel)
                except:
                    pass
                
                
            self.st_layer_id = ''
      
            # set new layer instance
            if SensorThingLayerUtils.isSensorThingLayer(layer):
                self.st_layer_id = layer.id()
                
                layer.styleChanged.connect(self.updateStylePanel)
                
                layer.temporalProperties().changed.connect(self.updateAnTemporalPanel)
                
                # populate settings dictionary
                if self.st_layer_id not in self.layerSetting:
                    self.layerSetting[self.st_layer_id] = self.getLayerInitSetting()
            
        # Initialize style panel
        self.updatePanels()
        
        
    
    def eventFilter(self, source, event):
        """ Filter widget events"""
        if isinstance( source, QgsAbstractDataSourceWidget ):
            if event.type() == QEvent.KeyPress:
                if event.key() == Qt.Key_Escape:
                    return True
            return False
        else:
            return super().eventFilter(source, event)
    
    
    def updatePanels(self):
        """Update panel tab"""
        
        # Init
        has_layer = self.getLayer() is not None
        
        # Initialize Style tab
        self.updateStylePanel()
        
        # Initialize Analyze tab
        self.updateAnalyzePanel()
        
        # Initialize Export tab
        self.tabExport.setEnabled(has_layer)
    
    
    def updateStylePanel(self):
        """Update layer style tab"""
        
        try:
            # Check if updating
            if self.updating:
                return
        
            self.updating = True
            
            # Initialize style panel
            layout = self.pnlStyleWidget.layout()
            
            if self.st_style_widget is not None:
                self.st_style_widget.widgetChanged.disconnect(self.onStyleWidgetChanged)
                layout.removeWidget(self.st_style_widget)
                
            self.st_style_widget = None
            
            if self.st_style_dialog is not None:
                layout.removeWidget(self.st_style_dialog)
            self.st_style_dialog = None
            
            self.btnStyleApply.setEnabled(False)
            
            # Check if layer not none (if SensorThings layer)
            if self.getLayer() is None:
                self.lblNoStyle.setText(self.tr("Select a SensorThings layer"))
                self.lblNoStyle.setVisible(True)
                self.pnlStyle.setEnabled(False)
                return
            
            # Check if Vector layer with geometries (no table)
            elif self.getLayer().geometryType() == Qgis.GeometryType.Null:
                self.lblNoStyle.setText(self.tr("Layer without geometries"))
                self.lblNoStyle.setVisible(True)
                self.pnlStyle.setEnabled(False)
                return
            
            self.lblNoStyle.setVisible(False)
            self.pnlStyle.setEnabled(True)
                
            # Add layer Renderer Dialog as sub widget
            style = QgsStyle.defaultStyle()
            
            self.st_style_dialog = QgsRendererPropertiesDialog(self.getLayer(), style, True, None)
            
            if self.st_style_dialog is not None:
                self.st_style_dialog.widgetChanged.connect(self.onStyleWidgetChanged)
                layout.insertWidget(0, self.st_style_dialog)
        
        except Exception as e:
            # Show exception message
            logger.msgbar(
                logger.Level.Critical, 
                "{}: {}".format(self.tr("Cannot create style widget:"), str(e)),
                title=__QGIS_PLUGIN_NAME__)
            
        finally:
            self.updating = False
    
    
    def updateAnalyzePanel(self):
        """Update analyze panel"""
        
        # Check if layer is not none
        layer = self.getLayer()
        
        if layer is None:
            self.tabAnalysis.setEnabled(False)
            return
        
        laySettings = self.getLayerSettings()
        
        self.tabAnalysis.setEnabled(True)
        
        # Check if layer with geometry
        hasGeometryField = layer.geometryType() != Qgis.GeometryType.Null
        
        if hasGeometryField:
            self.gbxSpatial.setEnabled(True)
        
        else:
            laySettings['Analysis']['Spatial']['Collapsed']= True
            
            self.gbxSpatial.setEnabled(False)
        
        # Check if layer with DateTime fields
        hasDateTimeFields = False
        
        for field in layer.fields():
            if field.type() == QMetaType.QDateTime:
                hasDateTimeFields = True
                break
        
        spatial_layout = self.pnlAnSpatialWidget.layout()    
            
        if self.st_temporal_settings_widget is not None:
            spatial_layout.removeWidget(self.st_temporal_settings_widget)
            
        self.st_temporal_settings_widget = None
        
        if hasDateTimeFields:
            self.gbxTemporal.setEnabled(True)
            
            self.st_temporal_settings_widget = QgsVectorLayerTemporalPropertiesWidget(None, layer)
            
            spatial_layout.insertWidget(0, self.st_temporal_settings_widget)
            
        else:
            laySettings['Analysis']['Temporal']['Collapsed']= True
            
            self.gbxTemporal.setEnabled(False)
            
        # Check if layer has 'ObservedProperty' entity
        lay_entities = SensorThingLayerUtils.getExpandedEntities(layer)
        
        lay_entities.append(SensorThingLayerUtils.getEntity(layer))
        
        if  'ObservedProperty' in lay_entities:
            self.gbxObservProperty.setEnabled(True)
            self.cmbObservProperty.setEnabled(True)
            
            # populate ObservedProperty combo
            self.getObservedProperties()
               
            self.cmbObservProperty.clear()
                
            model = self.cmbObservProperty.model()
        
            for pair in laySettings['Analysis']['ObservProperty']['Data']:
                item = QStandardItem()
                item.setText(pair[1])
                item.setData(pair[0], Qt.UserRole)
                model.appendRow(item)
            
            model.sort(0)
                
            checked_items = laySettings['Analysis']['ObservProperty']['CheckedItems']
            
            self.cmbObservProperty.setCheckedItems(checked_items)
        
        else:
            laySettings['Analysis']['ObservProperty']['Collapsed']= True
            
            self.gbxObservProperty.setEnabled(False)
            
            
        
        
        # Set widgets for layer settings
        self.gbxTemporal.setCollapsed(laySettings['Analysis']['Temporal']['Collapsed'])
        
        self.gbxSpatial.setCollapsed(laySettings['Analysis']['Spatial']['Collapsed'])
        
        self.gbxObservProperty.setCollapsed(laySettings['Analysis']['ObservProperty']['Collapsed'])
        
        
    def getObservedProperties(self):
        """Load ObservProperty data for panel layer"""
        
        # Check if data already loaded
        laySettings = self.getLayerSettings()
                
        if laySettings['Analysis']['ObservProperty']['Data']:
            return
        
        laySettings['Analysis']['ObservProperty']['Data'] = {}
        """
        # Check if load all ObservedProperty names or only in layer features (may be very slow!!!)
        search_layer = self.getLayer()
        
        names_by_features = plgConfig.get_value("analysis/observerd_properties_by_features", False)
        
        if not names_by_features:
            provider = search_layer.dataProvider()
            
            uri = provider.uri()
            
            search_layer = SensorThingLayerUtils.createLayer(
                name = 'ObservedProperty', 
                ds_uri = SensorThingLayerUtils.createDataSourceUri(ds_uri=uri, url=uri.param('url'), entity='ObservedProperty'))
            
        # Load data
        name_fld = SensorThingLayerUtils.formatFieldName(search_layer, 'ObservedProperty', 'name')
        
        desc_fld = SensorThingLayerUtils.formatFieldName(search_layer, 'ObservedProperty', 'description')
        
        laySettings['Analysis']['ObservProperty']['Data'] = set([(f[name_fld], f[desc_fld]) for f in search_layer.getFeatures()])
        """
        
    def updateAnTemporalPanel(self):
        """Update temporal panel"""
        
        if self.st_temporal_settings_widget is None:
            return 
        
        self.st_temporal_settings_widget.syncToLayer()
        
        
        
        
    def showTemporalControlWidget(self, show: bool = True):  
        """Show\Hide canvas temporal control widget"""
        
        # Check if valid temporal control
        temporal_control = iface.mapCanvas().temporalController()   
        if temporal_control is None:
            return
        
        # Get parent dockable widget
        dock_widget = QtWidgetUtils.getParentWidgetOfType(temporal_control.parent(), QDockWidget)
        if dock_widget is None:
            return
        
        # Show\Hide dockable widget
        if show:
            dock_widget.show()
        else:
            dock_widget.hide()
        
        
        
        