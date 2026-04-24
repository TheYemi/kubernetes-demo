from flask import Flask, render_template, request, redirect
import requests
import os
import json

app = Flask(__name__)

api_url = os.environ.get('API_URL', 'http://api')

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