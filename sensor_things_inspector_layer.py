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
import json

from qgis.PyQt.QtCore import pyqtSignal, pyqtSlot, QCoreApplication

from qgis.core import Qgis, QgsApplication, QgsDataSourceUri, QgsMessageLog, QgsVectorLayer, QgsFeature, QgsTask

LOG_TAG = 'SensorThings'

#: Constant for provider name  
__SENSORTHINGS_PROVIDER_NAME__ = 'sensorthings'

#
#------------------------------------------------
class SensorThingLoadDataTask(QgsTask):
    """QGIS task to load data using SensorThings provider."""

    # signals 
    resolved = pyqtSignal(list)
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
            self.exception = None
            self.error_message = ''
            self.data = self.fetch_data(self.uri, self.prefix_attribs, self.rename_attribs)
            return True
        except Exception as ex:
            self.exception = ex
            return False

    @staticmethod
    def fetch_data(ds_uri: QgsDataSourceUri, prefix_attribs: str = '', rename_attribs=None) -> list:
        """Load SensorThings data synchronously for WebChannel requests."""
        rename_attribs = rename_attribs or {'id': '@iot.id', 'selfLink': '@iot.selfLink'}
        uri_str = ds_uri.uri(False)

        query_layer = SensorThingLayerUtils.createLayer("SensorThingLoadDataTask", ds_uri)
        if not query_layer.isValid():
            err = ''
            try:
                layer_error = query_layer.error()
                if layer_error:
                    err = layer_error.message()
            except Exception:
                pass
            msg = "{} ({})".format(
                SensorThingLayerUtils.tr("Cannot create SensorThings query layer"),
                err or uri_str,
            )
            QgsMessageLog.logMessage(msg, LOG_TAG, Qgis.Critical)
            raise Exception(msg)

        data = []
        for feature in query_layer.getFeatures():
            attribs = {
                str(k): SensorThingLoadDataTask._normalize_value(v)
                for k, v in feature.attributeMap().items()
            }
            attribs = SensorThingLoadDataTask._filter_attribs(attribs, prefix_attribs)
            row = SensorThingLoadDataTask._rename_attribs(attribs, rename_attribs)
            data.append(row)

        return data

    @staticmethod
    def _qt_value_to_iso(value):
        """Convert Qt date/time values to ISO strings for JSON and JavaScript."""
        try:
            from qgis.PyQt.QtCore import QDate, QDateTime, Qt
            if isinstance(value, QDateTime):
                return value.toString(Qt.DateFormat.ISODateWithMs) if value.isValid() else None
            if isinstance(value, QDate):
                return value.toString(Qt.DateFormat.ISODate) if value.isValid() else None
        except (ImportError, AttributeError, TypeError):
            pass
        return None

    @staticmethod
    def _normalize_value(value):
        if value is None:
            return None
        try:
            from qgis.PyQt.QtCore import QVariant
            if isinstance(value, QVariant):
                if value.isNull():
                    return None
                return SensorThingLoadDataTask._normalize_value(value.value())
        except (ImportError, AttributeError, TypeError):
            pass
        if hasattr(value, 'isNull') and callable(value.isNull) and value.isNull():
            return None
        qt_iso = SensorThingLoadDataTask._qt_value_to_iso(value)
        if qt_iso is not None:
            return qt_iso
        if isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            text = value.strip()
            if text.startswith('{') or text.startswith('['):
                try:
                    return SensorThingLoadDataTask._normalize_value(json.loads(text))
                except (ValueError, TypeError):
                    pass
            return value
        if isinstance(value, dict):
            return {
                str(k): SensorThingLoadDataTask._normalize_value(v)
                for k, v in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [SensorThingLoadDataTask._normalize_value(v) for v in value]
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        return str(value)

    @staticmethod
    def page_data_to_json(page_data) -> str:
        return json.dumps(SensorThingLoadDataTask._normalize_value(page_data) or {})

    @staticmethod
    def as_json_string(records):
        return json.dumps(records or [])

    def finished(self, result: bool):
        """Override finished task method: send resolved/rejected events."""
        
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
    
    
    @staticmethod
    def _filter_attribs(rec: dict, prefix_attribs: str):
        if not prefix_attribs:
            return dict(rec)

        start_pos = len(prefix_attribs)
        filtered_rec = {}

        for k, v in rec.items():
            key = str(k)
            if key.startswith(prefix_attribs):
                filtered_rec[key[start_pos:]] = v

        return filtered_rec

    @staticmethod
    def _rename_attribs(rec: dict, rename_attribs: dict):
        rec = dict(rec)
        if rename_attribs and isinstance(rec, dict):
            for oldkey, newKey in rename_attribs.items():
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
    def getFeatureAttribute(feature: QgsFeature, attribute_name: str):
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

        