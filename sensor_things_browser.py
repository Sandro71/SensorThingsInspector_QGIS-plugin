# -*- coding: utf-8 -*-
"""SensorThingsWebView class

Description
-----------

This is QWebView customized subclass.

Libraries/Modules
-----------------

- None.
    
Notes
-----

- None.

Author(s)
---------

- Created by Sandro Moretti on 06/06/2022.
  Dedagroup Spa.

Members
-------
"""
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, pyqtSlot, pyqtProperty 
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QDialog
from PyQt5.QtQuick import QQuickView

from qgis.core import Qgis, QgsMessageLog
from qgis.gui import QgsGui

from SensorThingsAPI import __PLG_DEBUG__

import os

DEBUG_PORT = '5588'
DEBUG_URL = 'http://127.0.0.1:%s' % DEBUG_PORT

if __PLG_DEBUG__:
    os.environ['QTWEBENGINE_REMOTE_DEBUGGING'] = DEBUG_PORT

QML_DIR = os.path.join(os.path.dirname( os.path.abspath(__file__) ), 'qml/')
 
# 
#-----------------------------------------------------------
class SensorThingsRequestError(Exception):
    """Base class for other exceptions"""
 
#           
#-----------------------------------------------------------
class WebEngineInspectorDialog(QDialog):
    
    def __init__(self, parent=None, flags=Qt.WindowFlags()):
        """ """
        super().__init__(parent, flags)
        
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        self.url = DEBUG_URL
       
        # Dialog settings
        QgsGui.enableAutoGeometryRestore(self)
        
        self.setWindowTitle(self.tr("Web Engine Inspector"))
        
        self.setAutoFillBackground(True)
        
        self.setMinimumSize(900, 500)
        
        inspector = QQuickView()
        
        inspector.setResizeMode(QQuickView.SizeRootObjectToView)
        
        inspector.rootContext().setContextProperty("debug_url", self.url)
        
        inspector.setSource(QUrl.fromLocalFile(QML_DIR+'webinspector.qml'))
        
        container = QWidget.createWindowContainer(inspector, self)
        
        # Create layout and add widgets
        layout = QVBoxLayout()
        
        layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(container)
        
        # Set dialog layout
        self.setLayout(layout)
 
#----------------------------------------------------------- 
class WebEngineDialog(QDialog):
    
    urlChanged = pyqtSignal(str)
    
    htmlLoadRaised = pyqtSignal(str, str)
    
    runJavaScriptRaised = pyqtSignal(str)
    
    def __init__(self, parent=None, flags=Qt.WindowFlags()):
        """Constructor"""
        super().__init__(parent, flags)
        
        self._url = ""
        
        self._dlgInspector = None
        
        # Dialog settings
        #################self.setAttribute(Qt.WA_DeleteOnClose)
        
        QgsGui.enableAutoGeometryRestore(self)
        
        self.setWindowTitle(self.tr("SensorThings Identify"))
        
        self.setAutoFillBackground(True)
        
        self.setMinimumSize(900, 500)
        
        # Create widgets
        view = QQuickView()
        
        view.setTitle(self.tr("SensorThings Identify"))
        
        view.setResizeMode(QQuickView.SizeRootObjectToView)

        view.rootContext().setContextProperty("manager", self)
        
        view.setSource(QUrl.fromLocalFile(QML_DIR+'webengine.qml'))
 
        if view.status() == QQuickView.Error:
            for error in view.errors():
                QgsMessageLog.logMessage(error.description())
            return
        #
        container = QWidget.createWindowContainer(view)
        
        # Create layout and add widgets
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(container)
        
        # Set dialog layout
        self.setLayout(layout)
        
    def showInspector(self, dialog):
        """Show WebEngineView Inspector Dialog"""
        
        try:
            self._dlgInspector.close()
        except:
            pass
            
        self._dlgInspector = WebEngineInspectorDialog(parent=dialog)
        self._dlgInspector.show() 
        
    @pyqtProperty(str, notify=urlChanged)
    def url(self):
        return self._url
    
    @url.setter
    def url(self, u):
        if self._url != u:
            self._url = u
            self.urlChanged.emit(u)
     
    @pyqtSlot(str)
    def logError(self, message):
        ##logger.log(logger.Level.Critical, message, tag=__QGIS_PLUGIN_NAME__)
        QgsMessageLog.logMessage(message, "SensorThings", Qgis.Critical)
    
    @pyqtSlot(str)
    def logSslError(self, message):
        msg = "{}: {}".format(self.tr("SSL error"), message)
        self.logError(msg)
    
    """    
    @QtCore.pyqtSlot(str, result=str)
    def renderHtmlTemplate(self, templateName):
        pass
        
    def loadHtmlTemplate(self, templateName):
        s = manager.renderHtmlTemplate(templateName)
        self.htmlLoadRaised.emit(s)
    """
    
    @pyqtSlot(str,str)
    def setHtml(self, html, base):
        self.htmlLoadRaised.emit(html, base)
        
    def runJavaScript(self, script):
        self.runJavaScriptRaised.emit(script)
        
         