# -*- coding: utf-8 -*-
"""Module of SensorThingsAPI layer utilities.

Description
-----------

Libraries/Modules
-----------------
    
Notes
-----

- None.

Author
-------

- Created by Sandro Moretti
  2024 Dedagroup spa

Members
-------
"""
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QVariant, QCoreApplication

from qgis.core import QgsApplication, QgsDataSourceUri, QgsVectorLayer, QgsFeature, QgsTask



#: Constant for provider name  
__SENSORTHINGS_PROVIDER_NAME__ = 'sensorthings'

#
#------------------------------------------------
class SensorThingLoadDataTask(QgsTask):
    """QGIS task to load data using SensorThings provider."""

    # signals 
    resolved = pyqtSignal(QVariant)
    rejected = pyqtSignal(str)
    dataLoaded = pyqtSignal(QgsTask)

    def __init__(self, ds_uri: QgsDataSourceUri, prefix_attribs: str='', rename_attribs={}):
        """Constructor"""
        
        super().__init__('SensorThingLoadDataTask', QgsTask.CanCancel)
        
        self.uri = ds_uri
        self.rename_attribs = rename_attribs
        self.prefix_attribs = prefix_attribs
        
        self.exception = None
        self.error_message = ''
        self.data = []   
        
        self._silent_cancel = False
    
    
    @staticmethod
    def cancel_tasks(tasks: list):
        """Static method to cancel silently a list of SensorThingLoadDataTask"""
        if not isinstance(tasks, list):
            return
        
        for t in tasks:
            try:
                t.cancel_silently()
            except:
                pass
            
    
    @pyqtSlot()
    def get(self):
        """Start this task execution: scheduled in QGIS task manager."""
        QgsApplication.taskManager().addTask(self)


    def getUrl(self):
        """Returns the provider Url passed in object creation."""
        if not self.uri:
            return ''
        return self.uri.param('url') or ''
    
    
    def getFilter(self):
        """Return the provider filter passed in object creation."""
        if not self.uri:
            return None
        return self.uri.sql()       


    def run(self):
        """Override running task method."""
        try:
            # Init
            self.exception = None
            self.error_message = ''
            
            # Create query layer 
            query_layer = SensorThingLayerUtils.createLayer("SensorThingLoadDataTask", self.uri)
            
            if not query_layer.isValid():
                raise Exception(self.tr("Cannot create SensorThings query layer"))

            # Loop features
            for feature in query_layer.getFeatures():
                attribs = feature.attributeMap()
                self.data.append(self._renameKey(self._filter(attribs)))
             
            return True
            
        except Exception as ex:
            self.exception = ex
            return False
        
        
    def finished(self, result: bool):
        """Override finished task method: send resolved\rejected events."""
        
        # if task cancelled silently, does nothing
        if self._silent_cancel:
            return
        
        # Check if task terminated successfully
        if result:
            self.error_message = ''
            self.exception = None
            self.resolved.emit(self.data)
            
        # Check if task terminated abnormally without exception (maybe it was cancelled)
        elif self.exception is None:
            self.error_message = "'{name}' {msg}".format(name=self.description(), msg=self.tr('is terminated abnormally'))
            self.rejected.emit(self.error_message)
          
        # Check if task terminated abnormally due to an exception 
        else:
            self.error_message = "'{name}' {msg}: {exception}".format(name=self.description(), msg=self.tr('is terminated due to an exception'), exception=self.exception)
            self.rejected.emit(str(self.exception))
            
        self.dataLoaded.emit(self)


    def cancel(self):
        """Override cancel method sending events."""
        if not self._silent_cancel:
            self.error_message = "'{name}' {msg}".format(name=self.description(), msg=self.tr('cancelled'))
            self.dataLoaded.emit(self)
        
        super().cancel()
        
        
    def cancel_silently(self):
        """Cancel task without sending events."""
        self._silent_cancel = True
        self.cancel()
    
    
    def _filter(self, rec: dict):
        """Filter attributes using parameter passed in object creation."""
        if not self.prefix_attribs:
            return rec
        
        start_pos= len(self.prefix_attribs)
        
        filtered_rec = {}
        
        for k, v in rec.items():
            if k.startswith(self.prefix_attribs):
                key = k[start_pos:]
                filtered_rec[key] = v
                
        return filtered_rec
        
    
    def _renameKey(self, rec: dict):
        """Rename attributes using mapping parameter passed in object creation."""
        if self.rename_attribs and type(rec) is dict:
            for oldkey, newKey in self.rename_attribs.items():
                if oldkey in rec:
                    rec[newKey] = rec.pop(oldkey) 
        return rec


#
#-------------------------------------------------
class SensorThingLayerUtils: 

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
        return QCoreApplication.translate('SensorThingLayerUtils', message)

    @staticmethod
    def quoteValue(value):
        """Function to quote a value if string"""
        return rf"'{value}'" if isinstance(value, str) else value

    @staticmethod
    def getFeatureAttribute(feature: QgsFeature, attribute_name: str) -> QVariant:
        """Returns a feature attribute value"""
        attribute_name = attribute_name or ''
        
        index = feature.fieldNameIndex(attribute_name)
        if index == -1:
            raise NameError("{}: '{}'".format(SensorThingLayerUtils.tr("Attribute not found"), attribute_name))
        
        return feature.attribute(index)

    @staticmethod
    def isSensorThingLayer(layer: QgsVectorLayer) -> bool:
        """Check if a vector layer is a SensorThing layer"""
        
        # Check if layer is not none
        if layer is None:
            return False
        
        # Check if vector layer
        if not isinstance(layer, QgsVectorLayer):
            return False
        
        # Check if SensorThings layer
        provider = layer.dataProvider()
        
        if provider.name().lower() != __SENSORTHINGS_PROVIDER_NAME__:
            return False
        
        return True

    @staticmethod
    def getEntity(layer: QgsVectorLayer) -> bool:
        """Return the entity of SensorThing Layer"""
        provider = layer.dataProvider()
            
        provider_uri = provider.uri()
        
        return provider_uri.param('entity')
    
    @staticmethod
    def getExpandedEntities(layer: QgsVectorLayer) -> list:
        """Return the entity of SensorThing Layer"""
        expanded_entities = []
        
        provider = layer.dataProvider()
            
        provider_uri = provider.uri()
        
        expand_param = provider_uri.param('expandTo') or ''
        
        for token in expand_param.split(';'):
            entities_props = token.strip().split(':')
            expanded_entities.append(entities_props[0].strip())
            
        return expanded_entities

    @staticmethod
    def formatFieldName(layer: QgsVectorLayer, entity: str, field_name: str) -> str:
        # Check layer entity
        lay_entity = SensorThingLayerUtils.getEntity(layer)
        if lay_entity == entity:
            return field_name
        
        # Check layer expanded entities entities
        expande_entities = SensorThingLayerUtils.getExpandedEntities(layer)
        if entity in expande_entities:
            return "{}_{}".format(entity, field_name)
        
        return field_name
    
    @staticmethod
    def getUrl(layer: QgsVectorLayer) -> str:
        """Returns layer provider url"""
        provider = layer.dataProvider()
        
        provider_uri = provider.uri()
        
        return provider_uri.param('url') or ''
    
    @staticmethod
    def getFeatureLimit(layer: QgsVectorLayer, default_value: int=10000) -> int:
        """Returns layer feature limit"""
        if layer is None:
            return default_value
        
        provider = layer.dataProvider()
        
        provider_uri = provider.uri()
    
        feature_limit = provider_uri.param('featureLimit')
    
        try:
            return int(feature_limit)
        except ValueError:
            return default_value
    
    
    @staticmethod
    def createDataSourceUri(ds_uri: QgsDataSourceUri, url: str, entity: str, featureLimit: int=1000, expandTo: str=None, sql: str=None) -> QgsDataSourceUri:
        """Create a copy of a Data Source Uri specific for SensorThings provider"""
        
        # Set Uie Authentication parameters
        uri = QgsDataSourceUri()
        
        authConfigId = ds_uri.authConfigId()
        if authConfigId:
            uri.setAuthConfigId( authConfigId )

        username = ds_uri.username()
        if username:
            uri.setUsername( username )

        password = ds_uri.password()
        if password:
            uri.setPassword( password )

        uri.setHttpHeaders( ds_uri.httpHeaders() )

        # Set SensorThings parameters
        if url:
            uri.setParam('url', url)
        
        if entity:
            uri.setParam('entity', entity)
        
        if featureLimit:
            uri.setParam('featureLimit', str(featureLimit))
         
        if expandTo:
            uri.setParam('expandTo', expandTo)
        
        if sql:
            uri.setSql(sql)
          
        return uri
    
    @staticmethod
    def cloneDataSourceUri(ds_uri: QgsDataSourceUri) -> QgsDataSourceUri:
        """Create a copy of a Data Source Uri specific for SensorThings provider"""
        
        return SensorThingLayerUtils.createDataSourceUri(
            ds_uri,
            url= ds_uri.param('url'), 
            entity= ds_uri.param('entity'),
            featureLimit= ds_uri.param('featureLimit'), 
            expandTo= ds_uri.param('expandTo'), 
            sql= ds_uri.sql()
        )
        
            
    @staticmethod
    def createLayer(name: str, ds_uri: QgsDataSourceUri) -> QgsVectorLayer:
        """Create a new SensorThing layer"""
        
        uri = SensorThingLayerUtils.cloneDataSourceUri(ds_uri)
        
        return QgsVectorLayer(uri.uri(False), name, __SENSORTHINGS_PROVIDER_NAME__)

        