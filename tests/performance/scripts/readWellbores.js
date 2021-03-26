import http from 'k6/http';
import { check } from 'k6';

import { getParams, is2xx, logError, randomRecordId } from "./common.js";

export const options = {
    vus: __ENV.VUS,
    iterations: __ENV.ITER
};


export default function () {
    const baseUrl = `${__ENV.API_BASE_URL}`;
    const params = getParams();

    const response = http.get(`${baseUrl}/ddms/v2/wellbores/${randomRecordId('wellbore')}`, params);

    if (!is2xx(response.status)) {
        logError(params, response, baseUrl);
    }

    check(response, {
        'read wellbores data status == 200': r => r.status == 200
    });
}