from app import create_app
from app.extensions import db
from app.models import Hechshers, Users


def _csrf_header(client):
    cookie = client.get_cookie("csrf_token")
    if not cookie:
        return {}
    token = cookie.value if hasattr(cookie, "value") else str(cookie)
    return {"X-CSRF-Token": token}


def _bootstrap_core_data():
    # One hechsher is enough for /api/submissions/place validation.
    db.session.add(
        Hechshers(
            hechsher_display_name="Badatz",
            hechsher_symbol="/icons/badatz.png",
        )
    )

    admin = Users(user_email="admin@example.com", user_name="admin", user_status="admin")
    admin.set_password("AdminPass123!")
    db.session.add(admin)
    db.session.commit()


def test_e2e_register_login_submit_and_admin_approve():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite+pysqlite:///:memory:",
            "JWT_SECRET_KEY": "test-secret-key-1234567890-1234567890",
            "ANTHROPIC_API_KEY": "",  # keep moderation deterministic in tests
        }
    )

    with app.app_context():
        db.create_all()
        _bootstrap_core_data()

    user_client = app.test_client()

    # 1) Bootstrap CSRF cookie
    csrf_bootstrap = user_client.get("/api/csrf-token")
    assert csrf_bootstrap.status_code == 200

    # 2) Register (also logs user in via cookies)
    register_res = user_client.post(
        "/auth/register",
        json={
            "email": "user@example.com",
            "username": "user1",
            "password": "StrongPass123!",
        },
        headers=_csrf_header(user_client),
    )
    assert register_res.status_code == 201

    # 3) Submit new place
    submit_res = user_client.post(
        "/api/submissions/place",
        json={
            "submission_type": "new_place",
            "place_name": "Happy Path Shawarma",
            "street_address": "Main St 12, Jerusalem",
            "latitude": 31.778,
            "longitude": 35.235,
            "hechsher_ids": [1],
            "tags": ["restaurant", "meat"],
            "source": "manual",
        },
        headers=_csrf_header(user_client),
    )
    assert submit_res.status_code == 201
    body = submit_res.get_json()
    assert body["submission"]["submission_type"] == "new_place"
    submission_id = body["submission"]["submission_id"]

    # 4) Admin login in separate client/session
    admin_client = app.test_client()
    admin_client.get("/api/csrf-token")
    admin_login = admin_client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
        headers=_csrf_header(admin_client),
    )
    assert admin_login.status_code == 200

    # 5) Admin queue should contain submission
    queue_res = admin_client.get("/api/admin/submissions")
    assert queue_res.status_code == 200
    items = queue_res.get_json()["items"]
    assert any(item["submission_id"] == submission_id for item in items)

    # 6) Admin approve
    approve_res = admin_client.post(
        f"/api/admin/submissions/{submission_id}/approve",
        headers=_csrf_header(admin_client),
    )
    assert approve_res.status_code == 200
    approve_body = approve_res.get_json()
    assert approve_body["admin_review_status"] == "approved"
    assert approve_body["is_visible"] is True

