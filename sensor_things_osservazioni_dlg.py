# -*- coding: utf-8 -*-
"""Module to show observation of things

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
import os
import csv
import json

# Qgis\PyQt modules
from qgis.PyQt.QtCore import Qt, pyqtSlot
from qgis.PyQt.QtWidgets import QFileDialog
from qgis.PyQt import QtWidgets
from qgis.core import QgsDataSourceUri

# plugin modules
from SensorThingsAPI import __QGIS_PLUGIN_NAME__, plgConfig
from SensorThingsAPI.log.logger import QgisLogger as logger
from SensorThingsAPI.utils.file import FileUtil
from SensorThingsAPI.html.generate import htmlUtil 
from SensorThingsAPI.sensor_things_inspector_layer import (
    SensorThingLayerUtils,
    SensorThingLoadDataTask,
)
from SensorThingsAPI.sensor_things_browser import WebEngineDialog, SensorThingsRequestError


# 
#-----------------------------------------------------------
class SensorThingsObservationDialog(WebEngineDialog):
    """Dialog to show Observations info"""
    
    
    def __init__(self, plugin, parent=None):
        """Constructor
        
        :param parent: 
        :type parent: QtWidgets
        """
        # init
        super().__init__(parent)
        
        self.plugin = plugin
        self.page_data = {}
        self.csv_options = {}
        self._st_load_task = None
        self._st_load_tasks = []
        self._dataSourceUri = QgsDataSourceUri()
        
        self.setWindowTitle(self.tr("Observations"))
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setWindowModality(Qt.WindowModality.NonModal)
        
    
    def closeEvent(self, _):
        """Close event method"""
        # cancel all active tasks
        SensorThingLoadDataTask.cancel_tasks(self._st_load_tasks)
    
    
    def logError(self, message, level=logger.Level.Critical):
        """Log error message"""
        logger.msgbar(
            level, 
            str(message), 
            title=__QGIS_PLUGIN_NAME__,
            clear=True
        )
        
        logger.msgbox(
            level, 
            str(message),  
            title=__QGIS_PLUGIN_NAME__
        )
        
    
    def rejectRequest(self, message):
        """Show Observations dialog"""    
        message = str(message)
        self.logError(message)
        # hide spinner
        self._show_web_spinner(False)
        
    
    def show(self, data, ds_uri):
        """Show Osservazioni grid"""
        try:
            self._dataSourceUri = ds_uri
            self.page_data = data or {}
            self.csv_options = {}
            self.page_data['chart_opts'] = plgConfig.get_value('chart', {})

            template_name = 'observations.html'
            template = htmlUtil.generateTemplate(template_name)
            self.setHtml(template.render(self.page_data), htmlUtil.getBaseUrl())

            QtWidgets.QDialog.show(self)
            self.raise_()
            self.activateWindow()

        except SensorThingsRequestError as ex:
            logger.msgbar(
                logger.Level.Critical,
                "{}: {}".format(self.tr("Observations dialog visualization"), str(ex)), 
                title=__QGIS_PLUGIN_NAME__)
            
        except Exception as ex:
            logger.msgbar(
                logger.Level.Critical, 
                "{}: {}".format(self.tr("Observations dialog visualization"), str(ex)),
                title=__QGIS_PLUGIN_NAME__)
    
    
    def _show_web_spinner(self, show):
        if show:
            self.runJavaScript("sensorThingsShowSpinner(true);")
        else:
            self.runJavaScript("sensorThingsShowSpinner(false);")
    
    def _composePhenomenonTime(self, row):
        row = row or {}
        combined = row.get('phenomenonTime')
        if combined:
            return str(combined)
        start = row.get('phenomenonTimeStart', '')
        end = row.get('phenomenonTimeEnd', '')
        if start and end:
            return "{}/{}".format(start, end)
        return ''
    def _export_csv_callback(self, oss_data):
        """Private method to export observations to CSV file"""
        try:
            # check if visible 
            if not self.isVisible():
                return
            
            if not self.csv_options:
                return
            
            # hide spinner
            self._show_web_spinner(False)
            
            # init
            options = self.csv_options or {}
            export_fields = options.get('exportFields', {})
            open_file_flag = options.get('openFile', False)
            date_range_text = options.get('dateRange', '')
            file_name = options.get('fileName', '')
            file_name_proposed = file_name
            
            # check if valid result data
            if not isinstance(oss_data, list):
                raise ValueError(self.tr("Returned malformed data"))
            
            # check if there are records
            if not oss_data:
                logger.msgbox(
                    logger.Level.Warning, 
                    "{}: \n{}".format(self.tr("No Observation found in the range of dates"), date_range_text),
                    title=__QGIS_PLUGIN_NAME__
                )
                return
            
            # config export
            cfg_export = plgConfig.get_value('export',{})
            fld_delimiter = str(cfg_export.get('field_delimiter_char', '')).strip()
            fld_delimiter = fld_delimiter[:1] or ','
            
            # loop while file permission denied 
            while True:
                # ask where to save file    
                file_path, _ = QFileDialog.getSaveFileName(
                    self, self.tr('Save the Observations file'), file_name_proposed, 'CSV(*.csv)')
                if not file_path:
                    return
                    
                try:
                    # create CSV file
                    with open(str(file_path), 'w', newline='\n', encoding='utf-8') as stream:
                        writer = csv.writer( stream, delimiter=fld_delimiter, lineterminator='\n' )
                        # write header
                        writer.writerow(export_fields.keys())
                        # write records
                        for row in oss_data:
                            row_data = []
                            
                            # Compose and add phenomenonTime attribute
                            row['phenomenonTime'] = self._composePhenomenonTime(row)
                            
                            # get values
                            for _, fld in export_fields.items():
                                field_name = fld.get('field', '')
                                field_value = row.get(field_name, '')
                                try:
                                    if 'index' in fld:
                                        field_index = int(fld.get('index'))
                                        field_value = field_value[field_index]      
                                except (TypeError, IndexError):
                                    field_value = ''
                                
                                # collect value
                                row_data.append(field_value)
                                
                            # write record
                            writer.writerow(row_data)
                    
                    # open downloaded file
                    if open_file_flag:
                        os.startfile(os.path.normpath(file_path))
                    
                    # exit loop        
                    return
                
                except PermissionError as ex:
                    # correct name with a postfix
                    file_name_proposed, _ = FileUtil.getPrefixFileName(file_name)
                    # show alert message
                    self.logError(
                        "{}: \n{}".format(self.tr("File access denied"), file_path),
                        level=logger.Level.Warning)
                    
        except Exception as ex:
            self.logError(str(ex))
            return
    
    
    @pyqtSlot(str, result=int)
    def getLimit(self, name):
        if name == 'featureLimit':
            return SensorThingLayerUtils.getFeatureLimit(self.plugin.main_panel.getLayer())
        return self.plugin.main_panel.getObservationLimit(name)

    @pyqtSlot(str, str)
    def exportCSV(self, url, options_json):
        """Export observations to CSV (options as JSON string)."""
        try:
            options = json.loads(options_json) if options_json else {}
            self._show_web_spinner(True)
            self.csv_options = options

            self._st_load_task = self._create_load_task(
                url=url,
                entity=options.get('query_entity'),
                featureLimit=options.get('query_featureLimit', self.getLimit('observationLimit')),
                expandTo=options.get('query_expandTo'),
                sql=options.get('query_filter', "id eq ''"),
                prefix_attribs=options.get('query_prefix_attribs', 'Observation_'),
            )
            self._st_load_task.resolved.connect(self._export_csv_callback)
            self._st_load_task.get()

        except Exception as ex:
            self.logError(str(ex))
            return False
    