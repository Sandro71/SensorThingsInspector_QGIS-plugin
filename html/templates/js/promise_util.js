/**
 * SensorThingsAPI Plugin
 *
 *  Promise utility functions.
 *
 */


/**
 * Quotes a string value
 */
function quote(value) {
    if (typeof value == "string")
    {
        return "'" + value + "'";
    }
    return value;
}

async function unwrapChannel(value) {
    if (value && typeof value.then === 'function') {
        return await value;
    }
    return value;
}

function parsePageData(raw) {
    if (raw == null || raw === '') {
        return {};
    }
    if (typeof raw === 'string') {
        return JSON.parse(raw);
    }
    if (typeof raw === 'object' && !Array.isArray(raw)) {
        return raw;
    }
    return {};
}

function parseFetchResult(raw) {
    if (raw == null || raw === '') {
        return [];
    }
    if (typeof raw === 'string') {
        return JSON.parse(raw);
    }
    if (Array.isArray(raw)) {
        return raw;
    }
    return [];
}

function requestPromise(url, entity, featureLimit, expandTo, sql, prefix_attribs) {
    return (async function() {
        try {
            var requestId = await unwrapChannel(pyjsapi.startFetchRequest(
                String(url),
                String(entity),
                String(featureLimit),
                expandTo || '',
                sql || '',
                prefix_attribs || ''
            ));
            if (!requestId) {
                return [];
            }

            for (var attempts = 0; attempts < 2400; attempts++) {
                var raw = await unwrapChannel(pyjsapi.getFetchResult(String(requestId)));
                if (raw !== '' && raw != null) {
                    return parseFetchResult(raw);
                }
                await new Promise(function(resolve) { setTimeout(resolve, 50); });
            }
            return [];
        } catch (e) {
            console.error('requestPromise error:', e);
            return [];
        }
    })();
}
