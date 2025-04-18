import pytest
from flask import jsonify
from app.models import User

def test_register_user_success(client):
    """Test successful user registration."""
    response = client.post('/api/auth/register', json={
        'username': 'newuser',
        'email': 'new@example.com',
        'password': 'password123'
    })
    assert response.status_code == 201
    json_data = response.json
    assert json_data['username'] == 'newuser'
    assert json_data['email'] == 'new@example.com'
    assert 'id' in json_data
    assert 'password_hash' not in json_data # Ensure hash isn't returned

    # Check database
    user = User.query.filter_by(username='newuser').first()
    assert user is not None
    assert user.email == 'new@example.com'

def test_register_user_missing_fields(client):
    """Test registration with missing fields."""
    response = client.post('/api/auth/register', json={
        'username': 'anotheruser',
        # Missing email and password
    })
    assert response.status_code == 400
    assert b"Missing username, email, or password" in response.data

def test_register_user_duplicate_username(client, add_user):
    """Test registration with duplicate username."""
    add_user('existinguser', 'exists@example.com', 'password')
    response = client.post('/api/auth/register', json={
        'username': 'existinguser',
        'email': 'new@example.com',
        'password': 'password123'
    })
    assert response.status_code == 409
    assert b"Username or email already exists" in response.data

def test_register_user_duplicate_email(client, add_user):
    """Test registration with duplicate email."""
    add_user('anotheruser', 'exists@example.com', 'password')
    response = client.post('/api/auth/register', json={
        'username': 'newuser',
        'email': 'exists@example.com',
        'password': 'password123'
    })
    assert response.status_code == 409
    assert b"Username or email already exists" in response.data

def test_login_success(client, add_user):
    """Test successful login."""
    add_user('loginuser', 'login@example.com', 'password123')
    response = client.post('/api/auth/login', json={
        'username': 'loginuser',
        'password': 'password123'
    })
    assert response.status_code == 200
    assert 'access_token' in response.json

def test_login_wrong_password(client, add_user):
    """Test login with incorrect password."""
    add_user('loginuser', 'login@example.com', 'password123')
    response = client.post('/api/auth/login', json={
        'username': 'loginuser',
        'password': 'wrongpassword'
    })
    assert response.status_code == 401
    assert b"Invalid username or password" in response.data

def test_login_nonexistent_user(client):
    """Test login with a username that doesn't exist."""
    response = client.post('/api/auth/login', json={
        'username': 'nosuchuser',
        'password': 'password123'
    })
    assert response.status_code == 401
    assert b"Invalid username or password" in response.data

def test_get_current_user_success(client, auth_tokens):
    """Test retrieving current user info."""
    token = auth_tokens['tokens']['user_a']
    user_id = auth_tokens['ids']['user_a']

    response = client.get('/api/auth/me', headers={
        'Authorization': f'Bearer {token}'
    })
    assert response.status_code == 200
    json_data = response.json
    assert json_data['id'] == user_id
    assert json_data['username'] == 'user_a'
    assert json_data['email'] == 'a@test.com'

def test_get_current_user_unauthorized(client):
    """Test retrieving current user without token."""
    response = client.get('/api/auth/me')
    assert response.status_code == 401 # Expecting JWT Extended's unauthorized error
    assert b"Missing Authorization Header" in response.data # Check specific message

def test_get_current_user_invalid_token(client):
    """Test retrieving current user with invalid token."""
    response = client.get('/api/auth/me', headers={
        'Authorization': 'Bearer invalidtokenhere'
    })
    assert response.status_code == 422 # Expecting JWT Extended's invalid token error
    assert b"Invalid header padding" in response.data or b"Not enough segments" in response.data # Check specific message
