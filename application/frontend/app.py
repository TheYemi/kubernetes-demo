from flask import Flask, render_template_string, request, redirect
import requests
import os

app = Flask(__name__)

api_url = os.environ.get('API_URL', 'http://api')

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Task Tracker...</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
        h1 { color: #333; }
        .task { padding: 10px; margin: 5px 0; background: #f0f0f0; display: flex; justify-content: space-between; }
        form { margin: 20px 0; }
        input[type="text"] { padding: 10px; width: 70%; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
        .delete-btn { background: #dc3545; }
    </style>
</head>
<body>
    <h1>Task Tracker v2</h1>
    <form method="POST" action="/add">
        <input type="text" name="task" placeholder="Enter a task" required>
        <button type="submit">Add Task</button>
    </form>
    <h2>Tasks:</h2>
    {% for task in tasks %}
    <div class="task">
        <span>{{ task }}</span>
        <form method="POST" action="/delete" style="display:inline;">
            <input type="hidden" name="task" value="{{ task }}">
            <button type="submit" class="delete-btn">Delete</button>
        </form>
    </div>
    {% endfor %}
</body>
</html>
'''

@app.route('/')
def index():
    try:
        response = requests.get(f'{api_url}/tasks')
        tasks = response.json().get('tasks', [])
    except:
        tasks = []
    return render_template_string(HTML_TEMPLATE, tasks=tasks)

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
    app.run(host='0.0.0.0', port=5000)