import QtQuick 2.15
import QtWebChannel 1.15
import QtWebEngine 1.10

Item {

	WebChannel {
		id: channel
	}
	
	WebEngineView {
		id: webEngineView
		anchors.fill: parent
		url: manager.url
		webChannel: channel
		settings.pluginsEnabled: true
		settings.javascriptEnabled: true
		
		onLoadingChanged: function(request)
        {
			if(loadRequest.status == WebEngineView.LoadStartedStatus){
                channel.inject();
            }
            if(request.status === WebEngineLoadRequest.LoadFailedStatus)
            {
                manager.logError(request.errorDomain);
                manager.logError(request.errorString);
            }
        }
		
		onNavigationRequested: {
			//manager.logError(request.url);
            var schemaRE = /^file:|^data:/;
            if (schemaRE.test(request.url)) {
                request.action = WebEngineView.AcceptRequest;
            } else {
                request.action = WebEngineView.IgnoreRequest;
                // delegate request.url here
            }
		}
		
		onCertificateError: function(error) {
			manager.logSslError(error.description);
			error.ignoreCertificateError();
		}
		
		onContextMenuRequested: {
			request.accepted = true
		}
		
		function doLoadHtml(html, base) {
			webEngineView.loadHtml(html, base || "/");
			//manager.logError(webEngineView.url);
		}
		
		function doRunJavaScript(script) {
			webEngineView.runJavaScript(script, function(result) { console.log(result); });
		}
		
	}

	Component.onCompleted: {
		
		channel.registerObject("pyjsapi", manager);
	
		manager.htmlLoadRaised.connect(webEngineView.doLoadHtml);
		
		manager.runJavaScriptRaised.connect(webEngineView.doRunJavaScript);
		
	}
	
}