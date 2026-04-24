import pytest
from app import app
import json


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_index_page_loads(client, mocker):
    mocker.patch('requests.get', return_value=mocker.Mock(
        json=lambda: {'tasks': ['task1', 'task2']}
    ))
    
    response = client.get('/')
    
    assert response.status_code == 200
    assert b'Task Tracker' in response.data
    assert b'task1' in response.data


def test_index_page_api_failure(client, mocker):
    mocker.patch('requests.get', side_effect=Exception('API down'))
    
    response = client.get('/')
    
    assert response.status_code == 200
    assert b'Task Tracker' in response.data


def test_health_endpoint(client):
    response = client.get('/health')
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['status'] == 'healthy'


def test_add_task_redirect(client, mocker):
    mocker.patch('requests.post', return_value=mocker.Mock(status_code=201))
    
    response = client.post('/add', data={'task': 'New task'}, follow_redirects=False)
    
    assert response.status_code == 302  # Redirect
    assert response.location == '/'


def test_delete_task_redirect(client, mocker):
    mocker.patch('requests.delete', return_value=mocker.Mock(status_code=200))
    
    response = client.post('/delete', data={'task': 'task1'}, follow_redirects=False)
    
    assert response.status_code == 302  # Redirect
    assert response.location == '/'
