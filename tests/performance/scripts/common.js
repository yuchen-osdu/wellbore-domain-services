import { uuidv4 } from "https://jslib.k6.io/k6-utils/1.0.0/index.js";
import http from 'k6/http';

export const DATA_PARTITION_ID = __ENV.DATA_PARTITION_ID;
export const ACL_DOMAIN = __ENV.ACL_DOMAIN;
export const DL_GROUP_DOMAIN = `${DATA_PARTITION_ID}.${ACL_DOMAIN}`;
export const LEGAL_TAG = __ENV.LEGAL_TAG;

export const logsRecordIds = open('../data/log.json');
export const markersRecordIds = open('../data/marker.json');
export const wellboresRecordIds = open('../data/wellbore.json');

////////// Data generation functions ////////// 
/**
 * Generate a valid wks log metadata
 * API : /ddms/v2/log
 */
export function generateLogMetadata() {
    return [
        {
            'acl': {
                'owners': [`data.default.owners@${DL_GROUP_DOMAIN}`],
                'viewers': [`data.default.viewers@${DL_GROUP_DOMAIN}`]
            },
            "kind": `${DATA_PARTITION_ID}:wks:log:2.0.0`,
            "legal": {
                "legaltags": [
                    LEGAL_TAG,
                ],
                "otherRelevantDataCountries": [
                    "US",
                    "FR"
                ]
            },
            "data": {
                "md": {
                    "unitKey": "ft",
                    "value": 0
                },
                'name': `log-${flatUUID4()}`
            },
        }
    ];
};

/**
 * Generates a valid wks log bulkdata with the split orient
 * API : /ddms/v2/log/{logid}/data
 */
export function generateLogData() {
    let values = [];
    let columns = [];
    let index = [];

    for (var i = 0; i < 200; i++) {
        columns.push(i == 0 ? 'Ref' : `col_${i}`);
        index.push(i);
        let columnValue = [];
        for (var j = 0; j < 200; j++) {
            columnValue.push(getRandomFloat(0, 150));
        }
        values.push(columnValue);
    }
    return {
        'columns': columns,
        'index': index,
        'data': [values]
    };
}

/**
 * Generates a valid wks marker
 * API : /ddms/v2/markers
 */
export function generateMarker() {
    return [
        {
            "acl": {
                "owners": [
                    "data.default.owners@opendes.p4d.cloud.slb-ds.com"
                ],
                "viewers": [
                    "data.default.viewers@opendes.p4d.cloud.slb-ds.com"
                ]
            },
            "data": {
                "name": `marker-${flatUUID4()}`,
                "md": {
                    "unitKey": "ft",
                    "value": 0
                }
            },
            "id": `${DATA_PARTITION_ID}:marker:${flatUUID4()}`,
            "kind": `${DATA_PARTITION_ID}:osdu:marker:1.0.4`,
            "legal": {
                "legaltags": [
                    LEGAL_TAG
                ],
                "otherRelevantDataCountries": ["US", "FR"]
            }
        }
    ];
}
/**
 * Generates a valid wks wellbore
 * API : /ddms/v2/wellbores
 */
export function generateWellboresOSDU() {
    return [
        {
            "acl": {
                "owners": [
                    "data.default.owners@opendes.p4d.cloud.slb-ds.com"
                ],
                "viewers": [
                    "data.default.viewers@opendes.p4d.cloud.slb-ds.com"
                ]
            },
            "data": {
                "name": `wellbore-${flatUUID4()}`,
                "md": {
                    "unitKey": "ft",
                    "value": 0
                }
            },
            "id": `${DATA_PARTITION_ID}:wellbore:${flatUUID4()}`,
            "kind": `${DATA_PARTITION_ID}:osdu:wellbore:2.0.0`,
            "legal": {
                "legaltags": [
                    LEGAL_TAG
                ],
                "otherRelevantDataCountries": ["US", "FR"]
            }
        }
    ];
}

////////// Helper functions ////////// 

/**
 * This function will either call a local server that refreshes a token
 * or will return the token 
 * @returns {string} The JWT token
 */
export function getAuthToken() {
    const token = __ENV.TOKEN || "";
    /*
     This part is only useful when running long tests (test duration > 1h)
     This technique allows the refresh of token
     You will need to add your own implementation for the token server
     or contact wellbore ddms team for the example
    */
    if (token === "") {
        const provider = __ENV.CLOUD_PROVIDER || "azure";
        try {
            if (provider == 'azure') {
                return JSON.parse(http.get('http://localhost:3000/azure').body).token;
            } else {
                return JSON.parse(http.get('http://localhost:3000/gcp').body).token;
            }
        } catch (err) {
            return "";
        }
    } else {
        return token;
    }

}
/**
 * @return {any} the paramaters used for the test
 * this paramters include the headers with the JWT token, the correlation id and request id
 */
export function getParams() {
    const token = getAuthToken();
    const correlationId = `cid-wdms-perf-${uuidv4()}`;
    const requestId = `rid-wdms-perf-${uuidv4()}`;

    return { headers: { "Authorization": `Bearer ${token}`, 'data-partition-id': DATA_PARTITION_ID, "request-id": requestId, "correlation-id": correlationId } };
}

/**
 * checks if the response is succesful
 * @param {number} statusCode the status code of the response
 * @returns {Boolean} true if the status code is 2xx false if not
 */
export function is2xx(statusCode) {
    return parseInt(statusCode / 100) === 2;
}

/**
 * @param {*} params the parameters used during the test
 * @param {*} response The HTTP response 
 * @param {string} url the request url
 */
export function logError(params, response, url) {
    console.log('--- Start Logging Error ---');
    console.log(`Url : ${url}`);
    console.log(`Request Id : ${params.headers['request-id']} | Correlation Id : ${params.headers['correlation-id']}`);
    console.log(`Response Status Code : ${response.status}`);
    console.log(`Response Body : ${response.body}`);
    console.log('--- End Logging Error ---');
}

/**
 * 
 * @param {number} min the lower bound
 * @param {number} max the upper bound
 * @returns {number} a random number between max and min
 */
export function getRandomFloat(min, max) {
    return Math.floor(Math.random() * (max - min) + 100) / 100;
}


export function flatUUID4() {
    return uuidv4().toString().replace('-', '')
}

/**
 * 
 * @param {string} recordType either 'log' or 'marker' or 'wellbore'
 */
export function randomRecordId(recordType) {
    if (recordType == 'log') return logsRecordIds[Math.floor(Math.random() * logsRecordIds.length)];
    if (recordType == 'marker') return markersRecordIds[Math.floor(Math.random() * markersRecordIds.length)];
    if (recordType == 'wellbore') return wellboresRecordIds[Math.floor(Math.random() * wellboresRecordIds.length)];
}