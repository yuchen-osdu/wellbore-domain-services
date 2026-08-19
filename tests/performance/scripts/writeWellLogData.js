
import http from 'k6/http';
import { check } from 'k6';

import { generateWellLogData, getParams, is2xx, logError, randomRecordId } from "./common.js";

export const options = {
    vus: __ENV.VUS,
    iterations: __ENV.ITER
};

export default function () {
    const baseUrl = `${__ENV.API_BASE_URL}`
    const params = getParams();
    const payload = generateWellLogData();
    
    const response = http.post(`${baseUrl}/ddms/v3/welllogs/${randomRecordId('welllog')}/data`, JSON.stringify(payload), params);

    if (!is2xx(response.status)) {
        logError(params, response, baseUrl);
    }

    check(response, {
        'write log bulk data status == 200': r => r.status == 200
    });
}