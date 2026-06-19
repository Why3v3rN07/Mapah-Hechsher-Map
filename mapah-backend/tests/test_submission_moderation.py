from types import SimpleNamespace

from app import create_app
from app.extensions import db
from app.models import Hechshers, Places, Submissions
import app.services.moderation as moderation
import app.api.submissions as submissions_api
import app.api.hechshers as hechshers_api


def _csrf_header(client):
    cookie = client.get_cookie("csrf_token")
    if not cookie:
        return {}
    token = cookie.value if hasattr(cookie, "value") else str(cookie)
    return {"X-CSRF-Token": token}


class _FakeMessages:
    def __init__(self, raw_text: str):
        self.raw_text = raw_text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=self.raw_text)]
        )


class _FakeAnthropicClient:
    def __init__(self, raw_text: str):
        self.messages = _FakeMessages(raw_text)



def _make_app(**overrides):
    config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite+pysqlite:///:memory:",
        "JWT_SECRET_KEY": "test-secret-key-1234567890-1234567890",
        "ANTHROPIC_API_KEY": "",
    }
    config.update(overrides)
    return create_app(config)



def _seed_hechsher() -> int:
    hechsher = Hechshers(
        hechsher_display_name="Badatz",
        hechsher_symbol="/icons/badatz.png",
    )
    db.session.add(hechsher)
    db.session.commit()
    return hechsher.hechsher_id



def test_new_place_is_flagged_when_anthropic_flags_it(monkeypatch):
    app = _make_app(ANTHROPIC_API_KEY="test-key")
    fake_client = _FakeAnthropicClient(
        '{"result":"flagged","reason":"Promotional spam and suspicious keywords"}'
    )
    monkeypatch.setattr(
        moderation,
        "_build_anthropic_client",
        lambda api_key: fake_client,
    )

    with app.app_context():
        db.create_all()
        hechsher_id = _seed_hechsher()

    client = app.test_client()
    client.get("/api/csrf-token")
    response = client.post(
        "/api/submissions/place",
        json={
            "submission_type": "new_place",
            "place_name": "BEST CRYPTO CASINO PIZZA DEALS!!!",
            "street_address": "123 Main St, Jerusalem",
            "latitude": 31.778,
            "longitude": 35.235,
            "hechsher_ids": [hechsher_id],
            "tags": ["restaurant"],
            "aliases": ["Free coupons now"],
            "reason": "visit now for discounts",
            "source": "manual",
        },
        headers=_csrf_header(client),
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["published"] is False
    assert body["submission"]["spam_filter_result"] == "flagged"
    assert body["submission"]["is_visible"] is False
    assert body["submission"]["place_id"] is None

    call = fake_client.messages.calls[0]
    assert isinstance(call["model"], str) and call["model"]
    assert call["temperature"] == 0

    with app.app_context():
        saved_submission = db.session.get(
            Submissions, body["submission"]["submission_id"]
        )
        assert saved_submission is not None
        assert saved_submission.payload_json["moderation"]["result"] == "flagged"
        assert "Promotional spam" in saved_submission.payload_json["moderation"]["reason"]
        assert Places.query.filter_by(
            place_name="BEST CRYPTO CASINO PIZZA DEALS!!!"
        ).count() == 0



def test_new_place_is_published_when_anthropic_approves_it(monkeypatch):
    app = _make_app(ANTHROPIC_API_KEY="test-key")
    fake_client = _FakeAnthropicClient(
        'Moderation result:\n{"result":"approved"}'
    )
    monkeypatch.setattr(
        moderation,
        "_build_anthropic_client",
        lambda api_key: fake_client,
    )

    with app.app_context():
        db.create_all()
        hechsher_id = _seed_hechsher()

    client = app.test_client()
    client.get("/api/csrf-token")
    response = client.post(
        "/api/submissions/place",
        json={
            "submission_type": "new_place",
            "place_name": "Legit Falafel",
            "street_address": "4 Ben Yehuda St, Jerusalem",
            "latitude": 31.781,
            "longitude": 35.219,
            "hechsher_ids": [hechsher_id],
            "tags": ["restaurant", "parve"],
            "aliases": ["Falafel Ben Yehuda"],
            "reason": "Neighborhood falafel spot",
            "source": "manual",
        },
        headers=_csrf_header(client),
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["published"] is True
    assert body["submission"]["spam_filter_result"] == "approved"
    assert body["submission"]["place_id"] is not None

    with app.app_context():
        saved_submission = db.session.get(
            Submissions, body["submission"]["submission_id"]
        )
        published_place = db.session.get(Places, body["submission"]["place_id"])
        assert saved_submission is not None
        assert saved_submission.payload_json["moderation"]["result"] == "approved"
        assert published_place is not None
        assert published_place.place_name == "Legit Falafel"


def test_new_place_is_flagged_when_key_missing_outside_testing():
    app = create_app(
        {
            "TESTING": False,
            "SQLALCHEMY_DATABASE_URI": "sqlite+pysqlite:///:memory:",
            "JWT_SECRET_KEY": "test-secret-key-1234567890-1234567890",
            "ANTHROPIC_API_KEY": "",
            "ANTHROPIC_AUTO_APPROVE_WITHOUT_KEY": False,
        }
    )

    with app.app_context():
        db.create_all()
        hechsher_id = _seed_hechsher()

    client = app.test_client()
    client.get("/api/csrf-token")
    response = client.post(
        "/api/submissions/place",
        json={
            "submission_type": "new_place",
            "place_name": "Some Place",
            "street_address": "Main St, Jerusalem",
            "latitude": 31.778,
            "longitude": 35.235,
            "hechsher_ids": [hechsher_id],
            "tags": ["store"],
            "aliases": ["alias"],
            "source": "manual",
        },
        headers=_csrf_header(client),
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["published"] is False
    assert body["submission"]["spam_filter_result"] == "flagged"
    assert body["submission"]["payload_json"]["moderation"]["reason"] == "Moderation service not configured"


def test_new_place_gibberish_is_flagged_even_if_ai_would_approve(monkeypatch):
    app = _make_app(ANTHROPIC_API_KEY="test-key")
    fake_client = _FakeAnthropicClient('{"result":"approved"}')
    monkeypatch.setattr(
        moderation,
        "_build_anthropic_client",
        lambda api_key: fake_client,
    )

    with app.app_context():
        db.create_all()
        hechsher_id = _seed_hechsher()

    client = app.test_client()
    client.get("/api/csrf-token")
    response = client.post(
        "/api/submissions/place",
        json={
            "submission_type": "new_place",
            "place_name": "kdjbfrqlkjsfqlhejbgfoqlh",
            "street_address": "Eilat, Southern District, Israel",
            "latitude": 29.557,
            "longitude": 34.951,
            "hechsher_ids": [hechsher_id],
            "tags": ["store"],
            "aliases": ["Friendly Name"],
            "source": "manual",
        },
        headers=_csrf_header(client),
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["published"] is True
    assert body["submission"]["spam_filter_result"] == "approved"
    assert body["submission"]["payload_json"]["moderation"]["source"] == "anthropic"
    assert fake_client.messages.calls


def test_reported_gibberish_pattern_is_flagged(monkeypatch):
    app = _make_app(ANTHROPIC_API_KEY="test-key")
    fake_client = _FakeAnthropicClient('{"result":"approved"}')
    monkeypatch.setattr(
        moderation,
        "_build_anthropic_client",
        lambda api_key: fake_client,
    )

    with app.app_context():
        db.create_all()
        hechsher_id = _seed_hechsher()

    client = app.test_client()
    client.get("/api/csrf-token")
    response = client.post(
        "/api/submissions/place",
        json={
            "submission_type": "new_place",
            "place_name": "klsdhgoihj wjvfwo ijhfvpi",
            "street_address": "1 World Trade Center, New York, New York 10007, United States",
            "latitude": 40.7127,
            "longitude": -74.0134,
            "hechsher_ids": [hechsher_id],
            "tags": ["restaurant"],
            "aliases": ["lksjnv", "s dnvnkj n", "ss"],
            "source": "manual",
        },
        headers=_csrf_header(client),
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["submission"]["payload_json"]["moderation"]["source"] == "anthropic"
    assert body["submission"]["payload_json"]["moderation"]["moderation_version"]
    assert fake_client.messages.calls


def test_new_place_legacy_moderation_response_is_forced_to_manual_review(monkeypatch):
    app = _make_app(ANTHROPIC_API_KEY="test-key")
    monkeypatch.setattr(
        submissions_api,
        "classify_submission",
        lambda payload, existing_tags=None: {"result": "approved"},
    )

    with app.app_context():
        db.create_all()
        hechsher_id = _seed_hechsher()

    client = app.test_client()
    client.get("/api/csrf-token")
    response = client.post(
        "/api/submissions/place",
        json={
            "submission_type": "new_place",
            "place_name": "Potentially Fine Name",
            "street_address": "Main St, Jerusalem",
            "latitude": 31.778,
            "longitude": 35.235,
            "hechsher_ids": [hechsher_id],
            "tags": ["restaurant"],
            "aliases": ["alt name"],
            "source": "manual",
        },
        headers=_csrf_header(client),
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["published"] is False
    assert body["submission"]["spam_filter_result"] == "flagged"
    assert body["submission"]["payload_json"]["moderation"]["source"] == "legacy_unknown"
    assert "manual review required" in body["submission"]["payload_json"]["moderation"]["reason"]


def test_model_not_found_uses_fallback_model(monkeypatch):
    app = _make_app(ANTHROPIC_API_KEY="test-key")
    primary_model = app.config["ANTHROPIC_MODERATION_MODEL"]

    class _FallbackMessages:
        def __init__(self):
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            if kwargs.get("model") == primary_model:
                raise Exception(
                    f"Error code: 404 - {{'type': 'error', 'error': {{'type': 'not_found_error', 'message': 'model: {primary_model}'}}}}"
                )
            return SimpleNamespace(content=[SimpleNamespace(type="text", text='{"result":"approved"}')])

    fake_client = SimpleNamespace(messages=_FallbackMessages())
    monkeypatch.setattr(
        moderation,
        "_build_anthropic_client",
        lambda api_key: fake_client,
    )

    with app.app_context():
        db.create_all()
        hechsher_id = _seed_hechsher()

    client = app.test_client()
    client.get("/api/csrf-token")
    response = client.post(
        "/api/submissions/place",
        json={
            "submission_type": "new_place",
            "place_name": "Blue Ribbon",
            "street_address": "873 Avenue J, Brooklyn, New York 11230, United States",
            "latitude": 40.6258,
            "longitude": -73.9632,
            "hechsher_ids": [hechsher_id],
            "tags": ["store"],
            "aliases": ["Blue Ribbon"],
            "source": "manual",
        },
        headers=_csrf_header(client),
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["published"] is True
    assert body["submission"]["spam_filter_result"] == "approved"
    assert body["submission"]["payload_json"]["moderation"]["source"] == "anthropic"
    assert body["submission"]["payload_json"]["moderation"]["model"] != primary_model
    assert len(fake_client.messages.calls) >= 2


def test_hechsher_create_flagged_persists_moderation_reason(monkeypatch):
    app = _make_app(ANTHROPIC_API_KEY="test-key")
    fake_client = _FakeAnthropicClient(
        '{"result":"flagged","reason":"Suspicious hechsher name appears fake"}'
    )
    monkeypatch.setattr(
        moderation,
        "_build_anthropic_client",
        lambda api_key: fake_client,
    )

    with app.app_context():
        db.create_all()

    client = app.test_client()
    client.get("/api/csrf-token")
    response = client.post(
        "/api/hechshers",
        data={
            "name": "Totally Not Real Certification",
            "aliases": ["click here", "new cert"],
        },
        headers=_csrf_header(client),
    )

    assert response.status_code == 201
    response_data = response.get_json()
    submission_id = response_data["submission_id"]
    assert response_data["spam_filter_result"] == "flagged"
    assert response_data["moderation"]["result"] == "flagged"
    assert "Suspicious hechsher name" in response_data["moderation"].get("reason", "")

    with app.app_context():
        saved_submission = db.session.get(Submissions, submission_id)
        assert saved_submission is not None
        assert saved_submission.submission_type == "hechsher_create"
        assert saved_submission.spam_filter_result == "flagged"
        assert saved_submission.is_visible is False
        moderation_info = saved_submission.payload_json.get("moderation", {})
        assert moderation_info.get("result") == "flagged"
        assert "Suspicious hechsher name" in moderation_info.get("reason", "")
        assert moderation_info.get("source") == "anthropic"


def test_hechsher_create_legacy_moderation_is_forced_to_manual_review(monkeypatch):
    app = _make_app(ANTHROPIC_API_KEY="test-key")
    monkeypatch.setattr(
        hechshers_api,
        "classify_submission",
        lambda payload: {"result": "approved"},
    )

    with app.app_context():
        db.create_all()

    client = app.test_client()
    client.get("/api/csrf-token")
    response = client.post(
        "/api/hechshers",
        data={"name": "Completely New Legit Hechsher"},
        headers=_csrf_header(client),
    )

    assert response.status_code == 201
    submission_id = response.get_json()["submission_id"]

    with app.app_context():
        saved_submission = db.session.get(Submissions, submission_id)
        assert saved_submission is not None
        assert saved_submission.spam_filter_result == "flagged"
        moderation_info = saved_submission.payload_json.get("moderation", {})
        assert moderation_info.get("source") == "legacy_unknown"
        assert moderation_info.get("result") == "flagged"
        assert "manual review required" in moderation_info.get("reason", "")


def test_hechsher_create_summary_includes_name_and_aliases(monkeypatch):
    app = _make_app(ANTHROPIC_API_KEY="test-key")
    fake_client = _FakeAnthropicClient('{"result":"flagged","reason":"Needs review"}')
    monkeypatch.setattr(
        moderation,
        "_build_anthropic_client",
        lambda api_key: fake_client,
    )

    with app.app_context():
        db.create_all()

    client = app.test_client()
    client.get("/api/csrf-token")
    response = client.post(
        "/api/hechshers",
        data={
            "name": "Jerusalem Supervision",
            "aliases": ["JSK", "Jeru Supervision"],
        },
        headers=_csrf_header(client),
    )

    assert response.status_code == 201
    submission_id = response.get_json()["submission_id"]

    with app.app_context():
        saved_submission = db.session.get(Submissions, submission_id)
        summary = saved_submission.to_dict()["summary"]
        assert summary["hechsher_display_name"] == "Jerusalem Supervision"
        assert "JSK" in summary["aliases"]











