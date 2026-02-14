from flask import Flask, jsonify, request
import redis
import os

app = Flask(__name__)

redis_host = os.environ.get('REDIS_HOST', 'redis')
redis_password = os.environ.get('REDIS_PASSWORD', None)
redis_client = redis.Redis(host=redis_host, port=6379, password=redis_password, decode_responses=True)

@app.route('/health')
def health():
    try:
        # Actually test Redis connection
        redis_client.ping()
        return jsonify({'status': 'healthy', 'version': 'v2.0', 'redis': 'connected'}), 200
    except redis.ConnectionError as e:
        return jsonify({'status': 'unhealthy', 'version': 'v2.0', 'redis': 'disconnected', 'error': str(e)}), 503
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'version': 'v2.0', 'error': str(e)}), 503

@app.route('/tasks', methods=['GET'])
def get_tasks():
    tasks = redis_client.lrange('tasks', 0, -1)
    return jsonify({'tasks': tasks})

@app.route('/tasks', methods=['POST'])
def add_task():
    data = request.get_json()
    task = data.get('task')
    if task:
        redis_client.rpush('tasks', task)
        return jsonify({'message': 'Task added', 'task': task}), 201
    return jsonify({'error': 'No task provided'}), 400

@app.route('/tasks', methods=['DELETE'])
def delete_task():
    data = request.get_json()
    task = data.get('task')
    if task:
        redis_client.lrem('tasks', 1, task)
        return jsonify({'message': 'Task deleted'})
    return jsonify({'error': 'No task provided'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
