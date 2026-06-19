import io
import os

from app import create_app
from app.extensions import db


def _csrf_from_set_cookie(header_value: str) -> str:
    # Example: csrf_token=abc123; Expires=...; Path=/; SameSite=Lax
    return header_value.split(';', 1)[0].split('=', 1)[1]


def test_csrf_endpoint_sets_cookie():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite+pysqlite:///:memory:",
            "JWT_SECRET_KEY": "test-secret-key-1234567890-1234567890",
            "ANTHROPIC_API_KEY": "",
        }
    )

    with app.app_context():
        db.create_all()

    client = app.test_client()
    res = client.get('/api/csrf-token')

    assert res.status_code == 200
    assert 'csrf_token' in res.json
    set_cookie_headers = res.headers.getlist('Set-Cookie')
    assert any(h.startswith('csrf_token=') for h in set_cookie_headers)


def test_register_then_login_flow():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite+pysqlite:///:memory:",
            "JWT_SECRET_KEY": "test-secret-key-1234567890-1234567890",
            "ANTHROPIC_API_KEY": "",
        }
    )

    with app.app_context():
        db.create_all()

    client = app.test_client()

    csrf_res = client.get('/api/csrf-token')
    csrf_cookie = next(h for h in csrf_res.headers.getlist('Set-Cookie') if h.startswith('csrf_token='))
    csrf_token = _csrf_from_set_cookie(csrf_cookie)

    register_res = client.post(
        '/auth/register',
        json={
            'email': 'test@example.com',
            'username': 'tester',
            'password': 'StrongPass123!',
        },
        headers={'X-CSRF-Token': csrf_token},
    )

    assert register_res.status_code == 201
    assert register_res.json['user']['user_email'] == 'test@example.com'

    # Register rotates CSRF cookie, so use the fresh token for next state-changing call.
    new_csrf_cookie = next(
        h for h in register_res.headers.getlist('Set-Cookie') if h.startswith('csrf_token=')
    )
    csrf_token = _csrf_from_set_cookie(new_csrf_cookie)

    login_res = client.post(
        '/auth/login',
        json={'email': 'test@example.com', 'password': 'StrongPass123!'},
        headers={'X-CSRF-Token': csrf_token},
    )
    assert login_res.status_code == 200
    assert login_res.json['user']['user_name'] == 'tester'


def test_hechsher_icon_upload_saved_and_served():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite+pysqlite:///:memory:",
            "JWT_SECRET_KEY": "test-secret-key-1234567890-1234567890",
            "ANTHROPIC_API_KEY": "",
        }
    )

    with app.app_context():
        db.create_all()

    client = app.test_client()
    csrf_res = client.get('/api/csrf-token')
    csrf_cookie = next(h for h in csrf_res.headers.getlist('Set-Cookie') if h.startswith('csrf_token='))
    csrf_token = _csrf_from_set_cookie(csrf_cookie)

    upload_payload = {
        'name': 'Icon Test Hechsher',
        'icon': (io.BytesIO(b'test-image-bytes'), 'icon.png'),
    }
    create_res = client.post(
        '/api/hechshers',
        data=upload_payload,
        content_type='multipart/form-data',
        headers={'X-CSRF-Token': csrf_token},
    )

    assert create_res.status_code == 201
    icon_url = create_res.json['hechsher']['hechsher_symbol']
    assert icon_url.startswith('/api/hechshers/icons/')

    filename = icon_url.rsplit('/', 1)[-1]
    file_path = os.path.join(app.instance_path, 'uploads', 'hechshers', filename)
    assert os.path.exists(file_path)

    fetch_res = client.get(icon_url)
    assert fetch_res.status_code == 200
    assert fetch_res.data == b'test-image-bytes'




