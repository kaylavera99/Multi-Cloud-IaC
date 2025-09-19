import http from 'k6/http';
import { check, sleep } from 'k6';


export const options = {
    vus: 5,
    duration: '20s',
    thresholds: {
        http_req_failed: ['rate<0.01'], // <1% errors
        http_req_duration: ['p(95)<500'], // 95% of requests should be below 500ms
    },
};

const TARGET = __ENV.TARGET || 'http://localhost:8080/';
const EXPECT = __ENV.EXPECT_CLOUD || ''

export default function () {
    const res = http.get(TARGET);

    let j = null;
    try { j = res.json();} catch (_) {}

  
    check(res, {
        'status is 200 (ok)': (r) => r.status === 200,
        'json ok = true': () => j && j.ok === true,
        'cloud matches EXPECT (aws)': () => j && (!EXPECT || j.cloud === EXPECT),
    });
    sleep(0.1); // 

    }
