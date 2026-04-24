import pytest
from app import app
import json


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client, mocker):
    mocker.patch('app.redis_client.ping', return_value=True)
    
    response = client.get('/health')
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['status'] == 'healthy'
    assert data['version'] == 'v2.0'
    assert data['redis'] == 'connected'


def test_health_endpoint_redis_down(client, mocker):
    import redis
    mocker.patch('app.redis_client.ping', side_effect=redis.ConnectionError('Connection refused'))
    
    response = client.get('/health')
    data = json.loads(response.data)
    
    assert response.status_code == 503
    assert data['status'] == 'unhealthy'
    assert data['redis'] == 'disconnected'


def test_get_tasks_empty(client, mocker):
    mocker.patch('app.redis_client.lrange', return_value=[])
    
    response = client.get('/tasks')
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['tasks'] == []


def test_get_tasks_with_data(client, mocker):
    mocker.patch('app.redis_client.lrange', return_value=['task1', 'task2', 'task3'])
    
    response = client.get('/tasks')
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert len(data['tasks']) == 3
    assert 'task1' in data['tasks']


def test_add_task_success(client, mocker):
    mocker.patch('app.redis_client.rpush', return_value=1)
    
    response = client.post('/tasks', 
                          data=json.dumps({'task': 'New task'}),
                          content_type='application/json')
    data = json.loads(response.data)
    
    assert response.status_code == 201
    assert data['message'] == 'Task added'
    assert data['task'] == 'New task'


def test_add_task_no_data(client):
    response = client.post('/tasks',
                          data=json.dumps({}),
                          content_type='application/json')
    data = json.loads(response.data)
    
    assert response.status_code == 400
    assert 'error' in data


def test_delete_task_success(client, mocker):
    mocker.patch('app.redis_client.lrem', return_value=1)
    
    response = client.delete('/tasks',
                            data=json.dumps({'task': 'task1'}),
                            content_type='application/json')
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['message'] == 'Task deleted'


def test_delete_task_no_data(client):
    response = client.delete('/tasks',
                            data=json.dumps({}),
                            content_type='application/json')
    data = json.loads(response.data)
    
    assert response.status_code == 400
    assert 'error' in data
