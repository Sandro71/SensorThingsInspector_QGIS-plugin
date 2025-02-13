import QtQuick 2.15
import QtWebEngine 1.10

WebEngineView {
	id: webInspector
	anchors.fill: parent
	url: debug_url
}