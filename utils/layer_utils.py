# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LayerUtils
 
 The plugin enables QGIS software (www.qgis.org) to access dynamic data from sensors, 
 using SensorThingsAPI protocol (https://www.ogc.org/standards/sensorthings)
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2024-04-22
        git sha              : $Format:%H$
        copyright            : (C) 2024 by Deda Next (Sandro Moretti)
        email                : sandro.moretti@dedagroup.it
 ***************************************************************************/
"""
from functools import partial

from PyQt5.QtCore import Qt, QEventLoop, QVariant, QCoreApplication
from PyQt5.QtWidgets import QDialog, QComboBox
from qgis.core import (QgsWkbTypes, 
                       Qgis,
                       QgsApplication,
                       QgsProject,
                       QgsField, 
                       QgsMapLayer,
                       QgsVectorLayer, 
                       QgsVectorFileWriter, 
                       QgsVectorFileWriterTask)
from qgis.gui import QgsGui, QgsVectorLayerSaveAsDialog, QgsMessageViewer
from qgis.utils import iface


class QgisAppFieldValueConverter(QgsVectorFileWriter.FieldValueConverter):
    """Field value converter for export as vector layer"""
    def __init__(self, source_layer, attributesAsDisplayedValues, attributesExportNames):
        self.__mLayer = source_layer
        self.__mAttributesAsDisplayedValues = attributesAsDisplayedValues or []
        self.__mAttributesExportNames = attributesExportNames or []
        
        QgsVectorFileWriter.FieldValueConverter.__init__(self)
        
        
    def fieldDefinition(self, field: QgsField):
        if self.__mLayer is None:
            return field

        idx = self.__mLayer.fields().indexFromName( field.name() )
        # If not found in the original field name, it might be in the export names
        if idx == -1:
            idx = self.__mAttributesExportNames.indexOf( field.name() )

        if idx in self.__mAttributesAsDisplayedValues:
            return QgsField( field.name(), QVariant.String )
        
        return field
       
    
    def convert(self, idx: int, value: QVariant):
        if not self.__mLayer or not idx in self.__mAttributesAsDisplayedValues:
            return value
        
        setup = QgsGui.editorWidgetRegistry().findBest( self.__mLayer, self.__mLayer.fields().field( idx ).name() )
        fieldFormatter = QgsApplication.fieldFormatterRegistry().fieldFormatter( setup.type() )
        v = fieldFormatter.representValue( self.__mLayer, idx, setup.config(), QVariant(), value )
        return v
       

    def clone(self):
        return QgisAppFieldValueConverter(self.__mLayer, self.__mAttributesAsDisplayedValues, self.__mAttributesExportNames);
    
    
    
    
class LayerUtils: 

    @staticmethod
    def tr(message):
        """Get the translation for a string using Qt translation.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('LayerUtils', message)
    
    @staticmethod
    def updateLayerInToc(layer):
        """Force layer in TOC repainting"""
        renderer = layer.renderer()
        if renderer is not None:
            layer.setRenderer( renderer.clone() )
    
    @staticmethod
    def set_visibility(lay_list, show=True):
        """Set layers visibility"""
        if type(lay_list) is not list:
            return
        
        root_node = QgsProject.instance().layerTreeRoot()
        
        for layer in lay_list:
            if isinstance(layer, QgsMapLayer):
                lay_node = root_node.findLayer( layer.id() )
                lay_node.setItemVisibilityCheckedRecursive( show )
                

    @staticmethod
    def  saveAsVectorFile(vlayer: QgsVectorLayer, onlySelected: bool, addToMap: bool, dialogTitle: str = None, output_formats: list = None) -> str:
        """Export a vetor layer to an external file"""
        
        ########################################################################################################################
 
        def __onSuccess(newFilename: str, layerName: str, addToCanvas: bool, encoding: str, vectorFilename: str):
            
            if addToCanvas:
                uri = newFilename
                if layerName:
                    uri = f"{uri}|layername={layerName}"
                
                iface.addVectorLayer(uri, layerName, "ogr")
                #ok = false
                #QgsAppLayerHandling::addOgrVectorLayers( {uri}, encoding, QStringLiteral( "file" ), ok );
            """
            // We need to re-retrieve the map layer here, in case it's been deleted during the lifetime of the task
            if ( QgsVectorLayer *vlayer = qobject_cast< QgsVectorLayer * >( QgsProject::instance()->mapLayer( layerId ) ) )
              this->emit layerSavedAs( vlayer, vectorFileName );
            """
            iface.messageBar().pushMessage( LayerUtils.tr( "Layer Exported" ),
                                            "{} {}".format( LayerUtils.tr( "Successfully saved vector layer to:"), newFilename ),
                                            Qgis.MessageLevel.Success, -1 );

        def __onFailure(error: int, errorMessage: str):
            if error != QgsVectorFileWriter.Canceled:
                # Push error meessage on messageBar
                msgerr = "{}: {}".format( LayerUtils.tr( "Export to vector file failed: " ), errorMessage )
                
                iface.messageBar().pushMessage( LayerUtils.tr( "Layer Exported" ), msgerr, Qgis.MessageLevel.Critical, -1 );
                
                # Show error meessage dialog
                m = QgsMessageViewer( )
                m.setWindowTitle( LayerUtils.tr( "Save Error" ) )
                m.setMessageAsPlainText( msgerr )
                m.exec()
        
        ########################################################################################################################
        
        vectorFilename = None
        
        dialog = QgsVectorLayerSaveAsDialog(vlayer)
        if dialogTitle is not None:
            dialog.setWindowTitle( dialogTitle )
            
        dialog.setMapCanvas(  iface.mapCanvas() )
        dialog.setIncludeZ( QgsWkbTypes.hasZ( vlayer.wkbType() ) )
        dialog.setOnlySelected( onlySelected )
        dialog.setAddToCanvas( addToMap )
        
        # Filter output formats
        if output_formats is not None:
            # Find formats combo
            format_combo = dialog.findChild(QComboBox, "mFormatComboBox")
            if format_combo is not None:
                denied_formats = []
                
                # Find denied formats
                for i in range(format_combo.count()):
                    format_name = format_combo.itemData(i)
                    #print("{}: {}".format(format_combo.itemText(i), format_name))
                    if format_name not in output_formats:
                        denied_formats.append(format_name)
                        
                # Remove denied format in combo 
                for format_name in denied_formats:
                    index = format_combo.findData(format_name)
                    if index != -1:
                        format_combo.removeItem(index)    
        
        # Show export dialog
        if dialog.exec() != QDialog.Accepted:
            return vectorFilename
         
        # Export layer
        encoding = dialog.encoding()
        vectorFilename = dialog.fileName()
        out_format = dialog.format()
        datasourceOptions = dialog.datasourceOptions()
        autoGeometryType = dialog.automaticGeometryType()
        forcedGeometryType = dialog.geometryType()

        ct = None;
        destCRS = dialog.crs()

        if not destCRS.isValid():
            # QgsDatumTransformDialog::run( vlayer->crs(), destCRS, this, mMapCanvas );
            # ct = QgsCoordinateTransform( vlayer->crs(), destCRS, QgsProject::instance() );
            pass
            
        filterExtent = dialog.filterExtent()
        
        # No need to use the converter if there is nothing to convert
        converter = None
        if dialog.attributesAsDisplayedValues():
            converter = QgisAppFieldValueConverter(vlayer, dialog.attributesAsDisplayedValues(), dialog.attributesExportNames())
        
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = out_format
        options.layerName = dialog.layerName()
        options.actionOnExistingFile = dialog.creationActionOnExistingFile()
        options.fileEncoding = encoding
        
        if ct is not None:
            options.ct = ct
            
        options.onlySelectedFeatures = dialog.onlySelected()
        options.datasourceOptions = datasourceOptions
        options.layerOptions = dialog.layerOptions()
        options.skipAttributeCreation = not dialog.selectedAttributes()
        options.symbologyExport = dialog.symbologyExport()
        options.symbologyScale = dialog.scale()
        
        if dialog.hasFilterExtent():
            options.filterExtent = filterExtent
            
        options.overrideGeometryType = Qgis.WkbType.Unknown if autoGeometryType else forcedGeometryType
        options.forceMulti = dialog.forceMulti()
        options.includeZ = dialog.includeZ()
        options.attributes = dialog.selectedAttributes()
        options.attributesExportNames = dialog.attributesExportNames()
        
        if converter is not None:
            options.fieldValueConverter = converter
            
        options.saveMetadata = dialog.persistMetadata()
        options.layerMetadata = vlayer.metadata()

        addToCanvas = dialog.addToCanvas()
        writerTask = QgsVectorFileWriterTask( vlayer, vectorFilename, options )
        writerTask.completed.connect(lambda: QgsApplication.restoreOverrideCursor())
        writerTask.errorOccurred.connect(lambda: QgsApplication.restoreOverrideCursor())
        
        # when writer is successful:
        writerTask.completed.connect( partial(__onSuccess, addToCanvas=addToCanvas, encoding=encoding, vectorFilename=vectorFilename) )
        
        # when an error occurs:
        writerTask.errorOccurred.connect( __onFailure )
        
        QgsApplication.taskManager().addTask( writerTask )
        
        QgsApplication.setOverrideCursor(Qt.WaitCursor)
        QgsApplication.processEvents(QEventLoop.ExcludeUserInputEvents)
            
        return vectorFilename