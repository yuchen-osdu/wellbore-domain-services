
import http from 'k6/http';
import { check } from 'k6';

import { generateLogData, getParams, is2xx, logError } from "./common.js";
import { randomRecordId } from './dataset.js';

export const options = {
    vus: __ENV.VUS,
    iterations: __ENV.ITER
};

export default function () {
    const baseUrl = `${__ENV.API_BASE_URL}`
    const params = getParams();
    const payload = generateLogData();
    
    const response = http.post(`${baseUrl}/ddms/v2/logs/${randomRecordId()}/data?orient=split`, JSON.stringify(payload), params);

    if (!is2xx(response.status)) {
        logError(params, response, baseUrl);
    }

    check(response, {
        'write log bulk data status == 200': r => r.status == 200
    });
}