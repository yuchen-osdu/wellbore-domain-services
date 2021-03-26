
import http from 'k6/http';
import { check } from 'k6';

import { is2xx, getParams, logError, generateMarker } from "./common.js";

export const options = {
    vus: __ENV.VUS,
    iterations: __ENV.ITER
};

export default function () {
    const baseUrl = `${__ENV.API_BASE_URL}`;
    const params = getParams();
    const payload = generateMarker();

    let response = http.post(`${baseUrl}/ddms/v2/wellbores`, JSON.stringify(payload), params);
    
    if (!is2xx(response.status)) {
        logError(params, response, baseUrl);
    }

    check(response, {
        'write wellbores data status == 200': r => r.status == 200
    });
}


