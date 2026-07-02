# -*- coding: utf-8 -*-
"""WebEngine dialog base for SensorThings HTML views."""
from qgis.PyQt.QtCore import Qt, QUrl, pyqtSignal, pyqtSlot
from qgis.PyQt.QtWidgets import QVBoxLayout, QDialog, QSizePolicy

from qgis.core import Qgis, QgsMessageLog, QgsDataSourceUri
from qgis.gui import QgsGui

from SensorThingsAPI.sensor_things_inspector_layer import (
    SensorThingLayerUtils,
    SensorThingLoadDataTask,
)

try:
    from qgis.PyQt.QtWebEngineWidgets import QWebEngineView
    from qgis.PyQt.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
    from qgis.PyQt.QtWebChannel import QWebChannel

    _WEBENGINE_AVAILABLE = True
except ImportError:
    _WEBENGINE_AVAILABLE = False


class SensorThingsRequestError(Exception):
    """Base class for other exceptions"""


if _WEBENGINE_AVAILABLE:
    class _SensorThingsWebPage(QWebEnginePage):
        """Restrict navigation and accept self-signed certificates."""

        def __init__(self, manager, parent=None):
            super().__init__(parent)
            self._manager = manager
            self.certificateError.connect(self._on_certificate_error)

        def acceptNavigationRequest(self, url, _type, isMainFrame):
            return url.scheme() in ('file', 'data')

        def _on_certificate_error(self, error):
            self._manager.logSslError(error.description())
            error.acceptCertificate()


class WebEngineDialog(QDialog):

    htmlLoadRaised = pyqtSignal(str, str)
    runJavaScriptRaised = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._view = None
        self._channel = None
        self._web_layout = None
        self._dataSourceUri = QgsDataSourceUri()
        self._fetch_jobs = {}
        self._fetch_seq = 0

        QgsGui.enableAutoGeometryRestore(self)
        self.setWindowTitle(self.tr("SensorThings Identify"))
        self.setAutoFillBackground(True)
        self.setMinimumSize(900, 500)

        self._web_layout = QVBoxLayout()
        self._web_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._web_layout)

        self.htmlLoadRaised.connect(self._load_html)
        self.runJavaScriptRaised.connect(self._run_javascript)

        if not _WEBENGINE_AVAILABLE:
            QgsMessageLog.logMessage(
                self.tr("Qt WebEngine is not available."),
                "SensorThings",
                Qgis.Critical,
            )

    def _ensure_web_view(self):
        if self._view is not None or not _WEBENGINE_AVAILABLE:
            return

        self._view = QWebEngineView(self)
        self._view.setPage(_SensorThingsWebPage(self, self._view))
        self._view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        settings = self._view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)

        self._channel = QWebChannel(self._view)
        self._channel.registerObject("pyjsapi", self)
        self._view.page().setWebChannel(self._channel)

        self._web_layout.addWidget(self._view)
        self._view.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

    def _load_html(self, html, base):
        self._ensure_web_view()
        if self._view is not None:
            self._view.setHtml(html, QUrl(base or "/"))

    def _run_javascript(self, script):
        self._ensure_web_view()
        if self._view is not None:
            self._view.page().runJavaScript(script)

    @pyqtSlot(str)
    def logError(self, message):
        QgsMessageLog.logMessage(message, "SensorThings", Qgis.Critical)

    @pyqtSlot(str)
    def logSslError(self, message):
        self.logError("{}: {}".format(self.tr("SSL error"), message))

    @pyqtSlot(str, str)
    def setHtml(self, html, base):
        self.htmlLoadRaised.emit(html, base)

    def runJavaScript(self, script):
        self.runJavaScriptRaised.emit(script)

    @pyqtSlot(result=str)
    def getPageData(self):
        return SensorThingLoadDataTask.page_data_to_json(getattr(self, 'page_data', {}))

    def _parse_feature_limit(self, feature_limit):
        try:
            limit = int(feature_limit) if str(feature_limit).strip() else 0
        except (TypeError, ValueError):
            limit = 0
        if limit >= 1:
            return limit
        fl = self._dataSourceUri.param('featureLimit')
        try:
            return int(fl) if fl else 10000
        except (TypeError, ValueError):
            return 10000

    def _create_load_task(self, url, entity, featureLimit, expandTo, sql, prefix_attribs):
        uri = SensorThingLayerUtils.createDataSourceUri(
            self._dataSourceUri,
            url,
            entity,
            self._parse_feature_limit(featureLimit),
            expandTo or None,
            sql or None,
        )
        request = SensorThingLoadDataTask(
            uri,
            prefix_attribs=prefix_attribs or '',
            rename_attribs={'id': '@iot.id', 'selfLink': '@iot.selfLink'},
        )
        if hasattr(self, 'rejectRequest'):
            request.rejected.connect(self.rejectRequest)
        tasks = getattr(self, '_st_load_tasks', None)
        if tasks is not None:
            tasks.append(request)
        return request

    @pyqtSlot(str, str, str, str, str, str, result=str)
    def startFetchRequest(self, url, entity, featureLimit, expandTo, sql, prefix_attribs):
        try:
            self._fetch_seq += 1
            request_id = str(self._fetch_seq)
            self._fetch_jobs[request_id] = {'status': 'pending'}

            task = self._create_load_task(
                url, entity, featureLimit, expandTo, sql, prefix_attribs
            )

            def on_done(load_task):
                if load_task.exception:
                    err = str(load_task.exception)
                    self._fetch_jobs[request_id] = {'status': 'error', 'data': '[]', 'error': err}
                    self.logError(err)
                elif load_task.error_message and not load_task.data:
                    err = load_task.error_message
                    self._fetch_jobs[request_id] = {'status': 'error', 'data': '[]', 'error': err}
                    self.logError(err)
                else:
                    self._fetch_jobs[request_id] = {
                        'status': 'done',
                        'data': SensorThingLoadDataTask.as_json_string(load_task.data),
                    }

            task.dataLoaded.connect(on_done)
            task.get()
            return request_id

        except Exception as ex:
            self.logError(str(ex))
            return ''

    @pyqtSlot(str, result=str)
    def getFetchResult(self, request_id):
        job = self._fetch_jobs.get(str(request_id))
        if not job:
            return '[]'
        if job.get('status') == 'pending':
            return ''
        data = job.get('data', '[]')
        del self._fetch_jobs[str(request_id)]
        return data
