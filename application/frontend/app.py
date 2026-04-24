from flask import Flask, render_template, request, redirect
import requests
import os

app = Flask(__name__)

api_url = os.environ.get('API_URL', 'http://api')

@app.route('/')
def index():
    try:
        response = requests.get(f'{api_url}/tasks')
        tasks = response.json().get('tasks', [])
    except:
        tasks = []
    return render_template('index.html', tasks=tasks)

@app.route('/add', methods=['POST'])
def add():
    task = request.form.get('task')
    if task:
        requests.post(f'{api_url}/tasks', json={'task': task})
    return redirect('/')

@app.route('/delete', methods=['POST'])
def delete():
    task = request.form.get('task')
    if task:
        requests.delete(f'{api_url}/tasks', json={'task': task})
    return redirect('/')

@app.route('/health')
def health():
    return {'status': 'healthy'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # nosemgrep: python.flask.security.audit.app-run-param-config.avoid_app_run_with_bad_host