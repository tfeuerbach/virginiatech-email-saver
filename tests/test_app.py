import pytest
from web.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_homepage(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Virginia Tech Email Saver' in response.data

def test_submit_page(client):
    response = client.get('/submit')
    assert response.status_code == 405  # Method Not Allowed (since GET isn't allowed for /submit)
