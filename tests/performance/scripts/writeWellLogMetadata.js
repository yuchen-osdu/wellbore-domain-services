import http from 'k6/http';
import { check } from 'k6';

import { generateWellLogMetadata, getParams, is2xx, logError } from "./common.js";

export const options = {
    vus: __ENV.VUS,
    iterations: __ENV.ITER
};

export default function () {
    const baseUrl = `${__ENV.API_BASE_URL}`;
    const params = getParams();
    const payload = generateWellLogMetadata();

    const response = http.post(`${baseUrl}/ddms/v3/welllogs`, JSON.stringify(payload), params);

    if (!is2xx(response.status)) {
        logError(params, response, baseUrl);
    }

    check(response, {
        'write log meta data status == 200': r => r.status == 200
    });
}