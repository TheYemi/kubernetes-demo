from flask import Flask, jsonify, request
import redis
import os
import time
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from flask import Response

app = Flask(__name__)

redis_host = os.environ.get('REDIS_HOST', 'redis')
redis_password = os.environ.get('REDIS_PASSWORD', None)
redis_client = redis.Redis(host=redis_host, port=6379, password=redis_password, decode_responses=True)

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint', 'status_code'],
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0] 
)

REDIS_OPERATIONS = Counter(
    'redis_operations_total',
    'Total Redis operations',
    ['operation', 'status']
)

@app.before_request
def before_request():
    request._start_time = time.time()

@app.after_request
def after_request(response):
    if hasattr(request, '_start_time'):
        latency = time.time() - request._start_time
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.endpoint or 'unknown',
            status_code=response.status_code
        ).observe(latency)
        
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.endpoint or 'unknown',
            status=response.status_code
        ).inc()
    
    return response

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@app.route('/health')
def health():
    try:
        redis_client.ping()
        REDIS_OPERATIONS.labels(operation='ping', status='success').inc()
        return jsonify({'status': 'healthy', 'version': 'v2.0', 'redis': 'connected'}), 200
    except redis.ConnectionError as e:
        REDIS_OPERATIONS.labels(operation='ping', status='error').inc()
        return jsonify({'status': 'unhealthy', 'version': 'v2.0', 'redis': 'disconnected', 'error': str(e)}), 503
    except Exception as e:
        REDIS_OPERATIONS.labels(operation='ping', status='error').inc()
        return jsonify({'status': 'unhealthy', 'version': 'v2.0', 'error': str(e)}), 503

@app.route('/tasks', methods=['GET'])
def get_tasks():
    try:
        tasks = redis_client.lrange('tasks', 0, -1)
        REDIS_OPERATIONS.labels(operation='lrange', status='success').inc()
        return jsonify({'tasks': tasks})
    except Exception as e:
        REDIS_OPERATIONS.labels(operation='lrange', status='error').inc()
        return jsonify({'error': str(e)}), 500

@app.route('/tasks', methods=['POST'])
def add_task():
    data = request.get_json()
    task = data.get('task')
    if task:
        try:
            redis_client.rpush('tasks', task)
            REDIS_OPERATIONS.labels(operation='rpush', status='success').inc()
            return jsonify({'message': 'Task added', 'task': task}), 201
        except Exception as e:
            REDIS_OPERATIONS.labels(operation='rpush', status='error').inc()
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'No task provided'}), 400

@app.route('/tasks', methods=['DELETE'])
def delete_task():
    data = request.get_json()
    task = data.get('task')
    if task:
        try:
            redis_client.lrem('tasks', 1, task)
            REDIS_OPERATIONS.labels(operation='lrem', status='success').inc()
            return jsonify({'message': 'Task deleted'})
        except Exception as e:
            REDIS_OPERATIONS.labels(operation='lrem', status='error').inc()
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'No task provided'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # nosemgrep: python.flask.security.audit.app-run-param-config.avoid_app_run_with_bad_host