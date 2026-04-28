from flask import Flask, render_template, request, redirect, Response
import requests
import os
import time
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

api_url = os.environ.get('API_URL', 'http://api')

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
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
            endpoint=request.endpoint or 'unknown'
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

@app.route('/')
def index():
    try:
        response = requests.get(f'{api_url}/tasks')
        tasks_data = response.json().get('tasks', [])
        tasks = []
        for task in tasks_data:
            if '|||' in task:
                text, priority = task.split('|||', 1)
                tasks.append({'text': text, 'priority': priority})
            else:
                tasks.append({'text': task, 'priority': 'medium'})
    except:
        tasks = []
    return render_template('index.html', tasks=tasks)

@app.route('/add', methods=['POST'])
def add():
    task = request.form.get('task')
    priority = request.form.get('priority', 'medium')
    if task:
        task_data = f"{task}|||{priority}"
        requests.post(f'{api_url}/tasks', json={'task': task_data})
    return redirect('/')

@app.route('/delete', methods=['POST'])
def delete():
    task = request.form.get('task')
    priority = request.form.get('priority', 'medium')
    if task:
        task_data = f"{task}|||{priority}"
        requests.delete(f'{api_url}/tasks', json={'task': task_data})
    return redirect('/')

@app.route('/health')
def health():
    return {'status': 'healthy'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # nosemgrep: python.flask.security.audit.app-run-param-config.avoid_app_run_with_bad_host