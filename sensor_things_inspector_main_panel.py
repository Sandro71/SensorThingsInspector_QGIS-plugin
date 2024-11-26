# -*- coding: utf-8 -*-
"""SensorThingsInspector main panel

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

from PyQt5.QtCore import Qt, QEvent, QMetaType, QTimer
from PyQt5.QtWidgets import QDockWidget, QAbstractItemView

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.core import Qgis, QgsProject, QgsApplication, QgsStyle, QgsDataProvider, QgsVectorLayer
from qgis.gui import (QgsGui,
                      QgsRendererPropertiesDialog,
                      QgsAbstractDataSourceWidget,
                      QgsVectorLayerTemporalPropertiesWidget,
                      QgsCodeEditorSQL)

from qgis.utils import iface

from SensorThingsInspector import __QGIS_PLUGIN_NAME__, plgConfig
from SensorThingsInspector.log.logger import QgisLogger as logger
from SensorThingsInspector.utils.widget import QtWidgetUtils 
from SensorThingsInspector.utils.layer_utils import LayerUtils 
from SensorThingsInspector.sensor_things_inspector_layer import __SENSORTHINGS_PROVIDER_NAME__, SensorThingLayerUtils
from SensorThingsInspector.sensor_things_inspector_model import InspectorLimitModel, LimitDelegate

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/sensor_things_inspector_main_panel.ui'))
    

class SensorThingsInspectorMainPanel(QtWidgets.QDockWidget, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super().__init__(parent)
        
        self.source_selector = None
        self.source_widget = None
        self.sql_editor = None
        
        self.updating = False
        self.st_layer_id = ''
        self.st_style_widget = None
        self.st_style_dialog = None
        self.st_temporal_settings_widget = None
        
        self.temporal_needs_resync = False
        
        self.inspect_limits_model = None
        
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
        #####################################################################
        # Tab Control
        
        # Tab labels
        self.tabControl.setTabText(self.tabControl.indexOf(self.tabSource), self.tr("Source"))
        self.tabControl.setTabText(self.tabControl.indexOf(self.tabStyle), self.tr("Symbology"))
        self.tabControl.setTabText(self.tabControl.indexOf(self.tabAnalysis), self.tr("Temporal"))
        self.tabControl.setTabText(self.tabControl.indexOf(self.tabInspector), self.tr("Inspector"))
        
        # Tab Style Sheet
        themeName = QgsApplication.themeName()
        if re.search("Night", themeName, re.IGNORECASE) or re.search("Dark", themeName, re.IGNORECASE):
            self.tabControl.setStyleSheet("QTabBar::tab:selected { background-color: rgb(0, 0, 25); }")
        else:
            self.tabControl.setStyleSheet("QTabBar::tab:selected { background-color: rgb(121, 215, 255); }")
 
        #####################################################################
        # Tab Source
        
        self.btnSourceNew.setText(self.tr("New"))
        
        self.btnSourceApply.setText(self.tr("Apply"))
        
        self.btnQueryBuilder.setText(self.tr("Query Builder"))
        
        self.gbxSourceFilter.setTitle(self.tr("Filter"))
        
        self.btnProvider.clicked.connect(self.onSourceProvider)
        
        self.btnSourceNew.clicked.connect(self.onNewSource)
        
        self.btnSourceApply.clicked.connect(self.onSourceApply)
        
        self.btnQueryBuilder.clicked.connect(self.onQueryBuilder)
        
        #self.btnSourceApply.setEnabled(False)
        
        #####################################################################
        # Tab Symbology
        
        self.btnStyleReload.setText(self.tr("Reload"))
        
        self.btnStyleApply.setText(self.tr("Apply"))
        
        self.btnStyleReload.clicked.connect(self.onStyleReload)
        
        self.btnStyleApply.setEnabled(False)
        self.btnStyleApply.clicked.connect(self.onStyleApply)
        
        self.lblNoStyle.setText("")
        
        self.pnlStyle.setEnabled(False)
        
        ####################################################################
        # Tab Temporal
        
        self.btnAnalysisApply.setText(self.tr("Apply"))
        
        self.lblNoTemporal.setText("")
        
        self.btnAnalysisApply.clicked.connect(self.onAnalysisApply)
        
        #####################################################################
        # Tab Inspector
        
        self.inspect_limits_model = InspectorLimitModel()
        
        cfg_limits = plgConfig.get_value('inspector/limits',{})
        
        self.inspect_limits_model.setLimit('featureLimit',        cfg_limits.get('featureLimit'))
        self.inspect_limits_model.setLimit('thingLimit',          cfg_limits.get('thingLimit'))
        self.inspect_limits_model.setLimit('foiObservationLimit', cfg_limits.get('foiObservationLimit'))
        self.inspect_limits_model.setLimit('foiDatastreamLimit',  cfg_limits.get('foiDatastreamLimit'))
        self.inspect_limits_model.setLimit('datastreamLimit',     cfg_limits.get('datastreamLimit'))
        self.inspect_limits_model.setLimit('observationLimit',    cfg_limits.get('observationLimit'))
        
        self.tvwInspectorLimits.setModel(self.inspect_limits_model)
        
        self.tvwInspectorLimits.verticalHeader().hide()
        
        self.tvwInspectorLimits.horizontalHeader().setStretchLastSection(True)
        
        self.tvwInspectorLimits.setEditTriggers(QAbstractItemView.AllEditTriggers)
        
        self.tvwInspectorLimits.setItemDelegateForColumn(1, LimitDelegate(self))
        
        #####################################################################
        # Start
        self.layerSetting = {}
        
        iface.mapCanvas().renderComplete.connect( self.onRenderComplete )
        
        layer = iface.activeLayer()
        
        self.setLayer(layer)
    
    @property
    def HasValidLayer(self):
        """ Returns true if panel linked with valid STA layer """
        return self.getLayer() is not None
        
    @property
    def HasValidGeometryLayer(self):
        """ Returns true if panel linked with valid STA layer with geometry """
        layer = self.getLayer()
        return layer is not None and layer.geometryType() != Qgis.GeometryType.Null
    
    def onRenderComplete(self,  painter):
        """On Map Canvas render complete"""
        logger.restoreOverrideCursor()
        
    def onSourceProvider(self):
        """On provider source"""
        self.stackedWdSource.setCurrentIndex(0)
        
    def onNewSource(self):
        """On new source clicked"""
        #self.stackedWdSource.setCurrentIndex(0)
        
        layer = self.getLayer()
        if layer is None:
            return 
        
        if self.source_widget.sourceUri() is None:
            return
        
        new_source = self.source_widget.sourceUri()
        
        new_filter = '' if self.sql_editor is None else self.sql_editor.text()
  
        new_layer = self.addVectorLayer(new_source, layer.name(), layer.providerType())
        
        new_layer.setSubsetString( new_filter )
        
        
    def onSourceApply(self):
        """Apply layer source changes"""
        
        #self.btnSourceApply.setEnabled(False)
        
        layer = self.getLayer()
        if layer is None:
            return
        
        if self.source_widget is None:
            return
        
        new_source = self.source_widget.sourceUri()
        
        layer.setDataSource(new_source, layer.name(), layer.providerType(), QgsDataProvider.ProviderOptions())
        
        if self.sql_editor is not None:
            layer.setSubsetString( self.sql_editor.text() )
        
        
    def onSourceConfigChanged(self):
        """Slot for source configuration changed"""
        #self.btnSourceApply.setEnabled(True)
        pass
    
    def onQueryBuilder(self):
        """Show query builder dialog"""
        
        if self.sql_editor is None:
            return
        
        layer = self.getLayer()
        if layer is None:
            return
        
        filter_layer = QgsVectorLayer(layer.source(), layer.name(), layer.providerType())
        
        sql_dlg = QgsGui.subsetStringEditorProviderRegistry().createDialog( filter_layer, self )

        sql_dlg.setSubsetString( self.sql_editor.text() )
        
        if sql_dlg.exec():
            self.sql_editor.setText( sql_dlg.subsetString() )
        
    def onAddVectorLayer(self, vectorLayerPath: str, layerName: str, providerKey: str):
        """Adds a vector layer to the current project"""
        # Set wait cursor
        QTimer.singleShot(200, lambda: self.addVectorLayer(vectorLayerPath, layerName, providerKey))
        
    def addVectorLayer(self, vectorLayerPath: str, layerName: str, providerKey: str):
        """Adds a vector layer to the current project"""
        logger.setOverrideCursor(Qt.WaitCursor)
        
        #_ = iface.addVectorLayer(vectorLayerPath, layerName, providerKey)
        
        opts = QgsVectorLayer.LayerOptions()
        
        layer = QgsVectorLayer( vectorLayerPath, layerName, providerKey, options=opts )
        
        return QgsProject.instance().addMapLayer( layer, True )
     
    
  
    def onStyleWidgetChanged(self):
        """Slot for style definition changed"""
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
     
     
    def onLayerModified(self):
        """ """
        self.temporal_needs_resync = True       
            
    def onRepaintRequested(self):
        """ """
        if self.temporal_needs_resync:
            self.temporal_needs_resync = False
            
            self.onTemporalPropertiesChanged()
    
            
    def onTemporalPropertiesChanged(self):
        """Update temporal panel"""
        
        if self.st_temporal_settings_widget is None:
            return 
        
        self.st_temporal_settings_widget.syncToLayer()
    
    def getLimit(self, name):
        """Get a named limit value for inspector queries"""
        return self.inspect_limits_model.getLimit(name)
     
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
    
    
    def disconnectSignal(self, a_signal, a_slot):
        try:
            a_signal.disconnect(a_slot)
        except:
            pass
    
    
    def setLayer(self, layer):
        """Set layer instance to widget"""
        
        # Init
        wd_layer = self.getLayer()
        
        if layer != wd_layer: 
            # reset previous layer instance
            if wd_layer is not None:
                
                self.disconnectSignal(wd_layer.styleChanged, self.updateStylePanel)
                
                self.disconnectSignal(wd_layer.repaintRequested, self.onTemporalPropertiesChanged)
                
                self.disconnectSignal(wd_layer.temporalProperties().changed, self.onTemporalPropertiesChanged)
                
                self.disconnectSignal(wd_layer.layerModified, self.onTemporalPropertiesChanged)
                
            self.st_layer_id = ''
      
            # set new layer instance
            if SensorThingLayerUtils.isSensorThingLayer(layer):
                self.st_layer_id = layer.id()
                
                layer.styleChanged.connect(self.updateStylePanel)
                
                layer.layerModified.connect(self.onLayerModified)
                
                layer.temporalProperties().changed.connect(self.onTemporalPropertiesChanged)
                
                layer.repaintRequested.connect(self.onRepaintRequested)
                
                # populate settings dictionary
                if self.st_layer_id not in self.layerSetting:
                    self.layerSetting[self.st_layer_id] = self.getLayerInitSetting()
            
        # Initialize style panel
        self.updatePanels()
        
        
    
    def eventFilter(self, source, event):
        """ Filter widget events"""
        if isinstance( source, QgsAbstractDataSourceWidget ):
            
            if event.type() == QEvent.Close:
                event.ignore()
                return True
            
            elif event.type() == QEvent.KeyPress:
                if event.key() == Qt.Key_Escape:
                    return True
                
            return False
        else:
            return super().eventFilter(source, event)
    
    
    def updatePanels(self):
        """Update panel tab"""
        
        # Initialize Source tab
        self.updateSourcePanel()
        
        # Initialize Style tab
        self.updateStylePanel()
        
        # Initialize Temporal tab
        self.updateTemporalPanel()
    
    
    def updateSourcePanel(self):
        """Update layer source tab"""
        
        #self.btnSourceApply.setEnabled(False)
        
        # remove old source layer selection widget
        if self.source_selector is not None:
            self.source_selector.addVectorLayer.disconnect(self.onAddVectorLayer)
            self.source_selector.removeEventFilter(self)
            self.pageSourceSelection.layout().removeWidget(self.source_selector)
            
        self.source_selector = None
        
        # remove old source layer widget
        if self.source_widget is not None:
            self.pnlSourceWidget.layout().removeWidget(self.source_widget)
            
        self.source_widget = None
        
        # create source layer widget
        layer = self.getLayer()
        
        self.source_selector = QgsGui.sourceSelectProviderRegistry().createSelectionWidget(
            __SENSORTHINGS_PROVIDER_NAME__, self, Qt.Widget, 0)
         
        
        buttonBox = self.source_selector.findChild(QtWidgets.QDialogButtonBox)
        if buttonBox is not None:
            closeButton = buttonBox.button(QtWidgets.QDialogButtonBox.Close)
            if closeButton is not None:
                #closeButton.setEnabled(False)
                buttonBox.removeButton(closeButton)
   
        self.source_selector.setMapCanvas(iface.mapCanvas())    
        
        self.source_selector.addVectorLayer.connect(self.onAddVectorLayer)
                    
        self.pageSourceSelection.layout().insertWidget(0, self.source_selector)
        
        self.source_selector.installEventFilter(self)
        
        if layer is None:
            self.stackedWdSource.setCurrentIndex(0)
                
        else:
            self.stackedWdSource.setCurrentIndex(1)
            
            self.source_widget = QgsGui.sourceWidgetProviderRegistry().createWidget(layer, self)
            
            self.source_widget.setSourceUri(layer.dataProvider().uri().uri())
            
            self.source_widget.setMapCanvas(iface.mapCanvas())
            
            self.source_widget.changed.connect(self.onSourceConfigChanged)
            
            self.pnlSourceWidget.layout().insertWidget(0, self.source_widget)
            
            if buttonBox is not None:
                back_button = buttonBox.addButton(self.tr("Back"), QtWidgets.QDialogButtonBox.ApplyRole)
                back_button.setStyleSheet("font: bold;")
                back_button.clicked.connect(lambda checked, self=self: self.stackedWdSource.setCurrentIndex(1))
            
            
            if self.sql_editor is None:
                self.sql_editor = QgsCodeEditorSQL()
                self.pnlSourceFilter.layout().insertWidget(0, self.sql_editor)
            
            self.sql_editor.setText( layer.subsetString() )
    
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
    
    
    def updateTemporalPanel(self):
        """Update Temporal panel"""
        
        # remove temporal settings widget if present
        spatial_layout = self.pnlAnSpatialWidget.layout()
        
        if self.st_temporal_settings_widget is not None:
            spatial_layout.removeWidget(self.st_temporal_settings_widget)
            
        self.st_temporal_settings_widget = None
        
        # Check if layer is not none
        layer = self.getLayer()
        
        if layer is None:
            self.tabAnalysis.setEnabled(False)
            self.lblNoTemporal.setText(self.tr("Select a SensorThings layer"))
            self.lblNoTemporal.setVisible(True)
            self.btnAnalysisApply.setEnabled(False)
            return
        
        self.tabAnalysis.setEnabled(True)
        
        # Check if layer with DateTime fields
        hasDateTimeFields = False
        
        for field in layer.fields():
            if field.type() == QMetaType.QDateTime:
                hasDateTimeFields = True
                break
        
        if not hasDateTimeFields:
            self.lblNoTemporal.setText(self.tr("No temporal fields"))
            self.lblNoTemporal.setVisible(True)
            self.btnAnalysisApply.setEnabled(False)
  
        elif layer.geometryType() == Qgis.GeometryType.Null:
            self.lblNoTemporal.setText(self.tr("Layer without geometries"))
            self.lblNoTemporal.setVisible(True)
            self.btnAnalysisApply.setEnabled(False)
  
        else:
            self.st_temporal_settings_widget = QgsVectorLayerTemporalPropertiesWidget(None, layer)
            
            spatial_layout.insertWidget(0, self.st_temporal_settings_widget)
            
            self.lblNoTemporal.setVisible(False)
            
            self.btnAnalysisApply.setEnabled(True)
            
        
        
    
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
        
        
        
        