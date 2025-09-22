import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    //2 min ramp to 50VUs, hold 3mins, down 1min
    stages: [
        { duration: '2m', target: 50 },
        { duration: '3m', target: 50 },
        { duration: '1m', target: 0 },
    ],
    thresholds: {
        http_req_failed: ['rate<0.01'], // <1% errors
        http_req_duration: [
            'p(95)<300',
            'p(99)<800',
        ], // 95% of requests should be below 300ms, 99% below 800ms
    },
};  
const TARGET = __ENV.TARGET || 'http://localhost:8080/';
const EXPECT = __ENV.EXPECT_CLOUD || ''

export default function () {
    const res = http.get(TARGET, {tags: {name: 'GET /'}});

    let j = null;
  
    try { j = res.json();} catch (_) {}

    const okJson  = !!(j && j.ok === true);
    const okCloud = !!(j && (!EXPECT || j.cloud === EXPECT))
    check(res, {
        'status is 200 (ok)': () => res.status === 200,
        'json ok = true': () => j && j.ok === okJson,
        [`cloud matches EXPECT (${EXPECT || 'any'})`]: () => j && okCloud,
    });
    sleep(Math.random() * 0.4 + 1); //100 - 500ms; 100ms between requests
}