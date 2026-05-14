import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '1m', target: 30 },
    { duration: '3m', target: 30 },
    { duration: '1m', target: 60 },
    { duration: '2m', target: 60 },
    { duration: '1m', target: 0 },
  ],
};

const BASE_URL = __ENV.FRONTEND_URL || 'http://frontend.prod.svc.cluster.local:5000';

export default function () {
  let homeRes = http.get(`${BASE_URL}/`);
  check(homeRes, {
    'home page status is 200': (r) => r.status === 200,
  });

  sleep(2);

  let healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    'health check status is 200': (r) => r.status === 200,
  });

  sleep(3);
}