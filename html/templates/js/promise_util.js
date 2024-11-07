/**
 * SensorThings API Plugin
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

/**
 * Returns a promise about an asyncronous request
 * done by QGIS Api via Python injected object
 * (pyjsapi.getRequest)
 */
function requestPromise(url, entity, featureLimit, expandTo, sql, prefix_attribs) {
    return new Promise((resolve, reject) => {
        var request = pyjsapi.getRequest(url, entity, featureLimit, expandTo, sql, prefix_attribs);
        if (!request) {
            return reject("Impossibile istanziare una promessa di tipo Request.")
        }
        request.resolved.connect(resolve);
        request.rejected.connect(reject);
        request.get();
    });
}
