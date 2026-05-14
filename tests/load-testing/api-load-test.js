import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '1m', target: 50 },   
    { duration: '3m', target: 50 },   
    { duration: '1m', target: 100 },  
    { duration: '2m', target: 100 },  
    { duration: '1m', target: 0 },    
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], 
    http_req_failed: ['rate<0.01'],   
  },
};

const BASE_URL = __ENV.API_URL || 'http://api.prod.svc.cluster.local:5000';

export default function () {
  let healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    'health check status is 200': (r) => r.status === 200,
  });

  sleep(1);

  let tasksRes = http.get(`${BASE_URL}/tasks`);
  check(tasksRes, {
    'tasks status is 200': (r) => r.status === 200,
  });

  sleep(1);

  let createRes = http.post(
    `${BASE_URL}/tasks`,
    JSON.stringify({ title: 'Load test task', completed: false }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  check(createRes, {
    'create task status is 201': (r) => r.status === 201,
  });

  sleep(2);
}