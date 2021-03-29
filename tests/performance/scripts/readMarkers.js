import http from 'k6/http';
import { check } from 'k6';

import { getParams, is2xx, logError, randomRecordId } from "./common.js";

export const options = {
    vus: __ENV.VUS,
    iterations: __ENV.ITER
};

export default function () {
    const baseUrl = `${__ENV.API_BASE_URL}`;
    const markerId = "opendes:wellbore-ddms-test-marker:0000";
    const params = getParams();
    
    const response = http.get(`${baseUrl}/ddms/v2/markers/${randomRecordId('marker')}`, params);
    
    if (!is2xx(response.status)) {
        logError(params, response, baseUrl);
    }

    check(response, {
        'read markers data status == 200': r => r.status == 200
    });
}