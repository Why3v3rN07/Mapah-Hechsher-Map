from app import create_app
from app.extensions import db
from app.models import Hechshers, PlaceAliases, PlaceHechshers, PlaceTags, Places


def _csrf_header(client):
    cookie = client.get_cookie("csrf_token")
    if not cookie:
        return {}
    token = cookie.value if hasattr(cookie, "value") else str(cookie)
    return {"X-CSRF-Token": token}


def _seed_place_with_hechsher():
    hechsher = Hechshers(hechsher_display_name="Badatz", hechsher_symbol="/icons/badatz.png")
    db.session.add(hechsher)
    db.session.flush()

    place = Places(
        place_name="Alias Test Place",
        street_address="1 Main St, Jerusalem",
        latitude=31.77,
        longitude=35.21,
        is_active=True,
    )
    db.session.add(place)
    db.session.flush()

    db.session.add(PlaceHechshers(place_id=place.place_id, hechsher_id=hechsher.hechsher_id))
    db.session.add(PlaceTags(place_id=place.place_id, place_tag="restaurant"))
    db.session.commit()
    return hechsher.hechsher_id, place.place_id


def _make_app():
    return create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite+pysqlite:///:memory:",
            "JWT_SECRET_KEY": "test-secret-key-1234567890-1234567890",
            "ANTHROPIC_API_KEY": "",
        }
    )


def test_place_alias_submission_and_lookup():
    app = _make_app()
    with app.app_context():
        db.create_all()
        _, place_id = _seed_place_with_hechsher()

    client = app.test_client()
    client.get("/api/csrf-token")

    reg = client.post(
        "/auth/register",
        json={"email": "alias@example.com", "username": "aliasuser", "password": "StrongPass123!"},
        headers=_csrf_header(client),
    )
    assert reg.status_code == 201

    submit = client.post(
        f"/api/places/{place_id}/aliases",
        json={"aliases": ["Alias Cafe", "Alias Coffee"], "reason": "Common alternate names"},
        headers=_csrf_header(client),
    )
    assert submit.status_code == 201
    assert submit.get_json()["submission"]["submission_type"] == "alias_update"

    aliases_res = client.get(f"/api/places/{place_id}/aliases")
    assert aliases_res.status_code == 200
    assert set(aliases_res.get_json()["items"]) == {"Alias Cafe", "Alias Coffee"}


def test_submission_rate_limit_counts_only_successful_requests():
    app = _make_app()
    with app.app_context():
        db.create_all()
        hechsher_id, _ = _seed_place_with_hechsher()

    client = app.test_client()
    client.get("/api/csrf-token")

    invalid_1 = client.post(
        "/api/submissions/place",
        json={"submission_type": "new_place"},
        headers=_csrf_header(client),
    )
    invalid_2 = client.post(
        "/api/submissions/place",
        json={"submission_type": "new_place"},
        headers=_csrf_header(client),
    )
    assert invalid_1.status_code == 422
    assert invalid_2.status_code == 422

    valid_payload = {
        "submission_type": "new_place",
        "place_name": "Rate Limit Test Place",
        "street_address": "2 Main St, Jerusalem",
        "latitude": 31.778,
        "longitude": 35.235,
        "hechsher_ids": [hechsher_id],
        "tags": ["restaurant"],
        "source": "manual",
    }
    success_res = client.post(
        "/api/submissions/place",
        json=valid_payload,
        headers=_csrf_header(client),
    )
    assert success_res.status_code == 201

    limited_res = client.post(
        "/api/submissions/place",
        json=valid_payload,
        headers=_csrf_header(client),
    )
    assert limited_res.status_code == 429


def test_new_place_accepts_coordinates_only_and_saves_aliases():
    app = _make_app()
    with app.app_context():
        db.create_all()
        hechsher_id, _ = _seed_place_with_hechsher()

    client = app.test_client()
    client.get("/api/csrf-token")

    submit_res = client.post(
        "/api/submissions/place",
        json={
            "submission_type": "new_place",
            "place_name": "Coordinate Only Place",
            "street_address": "",
            "latitude": 31.786,
            "longitude": 35.223,
            "hechsher_ids": [hechsher_id],
            "tags": ["restaurant"],
            "aliases": ["Coord Place", "CP"],
            "source": "location_detect",
        },
        headers=_csrf_header(client),
    )
    assert submit_res.status_code == 201
    body = submit_res.get_json()
    place_id = body["submission"]["place_id"]
    assert place_id is not None

    with app.app_context():
        aliases = PlaceAliases.query.filter_by(place_id=place_id).all()
        assert {a.place_alias for a in aliases} == {"Coord Place", "CP"}


def test_places_supports_bbox_viewport_filtering():
    app = _make_app()
    with app.app_context():
        db.create_all()
        _seed_place_with_hechsher()
        db.session.add(
            Places(
                place_name="Haifa Test Place",
                street_address="3 Port St, Haifa",
                latitude=32.794,
                longitude=34.989,
                is_active=True,
            )
        )
        db.session.commit()

    client = app.test_client()

    jerusalem_bbox = "35.10,31.70,35.30,31.85"
    jerusalem_res = client.get(f"/api/places?bbox={jerusalem_bbox}")
    assert jerusalem_res.status_code == 200
    jerusalem_items = jerusalem_res.get_json()["items"]
    assert len(jerusalem_items) == 1
    assert jerusalem_items[0]["place_name"] == "Alias Test Place"

    invalid_res = client.get("/api/places?bbox=not,a,real,bbox")
    assert invalid_res.status_code == 400
    assert invalid_res.get_json()["code"] == "invalid_query"


