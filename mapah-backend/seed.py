import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone

from app import create_app
from app.extensions import db
from app.models import (
    HechsherAliases,
    Hechshers,
    PlaceAliases,
    PlaceHechshers,
    Places,
    PlaceTags,
    Submissions,
    UserPreferredHechshers,
    Users,
    RefreshToken,
    RefreshTokenFamily,
    RevokedToken,
)

app = create_app()

REQUIRED_TABLES = {
    "users",
    "hechshers",
    "hechsher_aliases",
    "places",
    "place_aliases",
    "place_tags",
    "place_hechshers",
    "user_preferred_hechshers",
    "submissions",
    "refresh_token_families",
    "refresh_tokens",
    "revoked_tokens",
}


def ensure_schema_ready() -> None:
    """Fail fast with a helpful message when migrations haven't been applied."""
    inspector = db.inspect(db.engine)
    existing = set(inspector.get_table_names())
    missing = sorted(REQUIRED_TABLES - existing)
    if missing:
        missing_list = ", ".join(missing)
        raise RuntimeError(
            "Database schema is not up to date. Missing tables: "
            f"{missing_list}. Run migrations first: "
            "python scripts/db_upgrade.py --seed --wipe"
        )


def auto_upgrade_schema() -> None:
    """Run migration upgrade helper before seeding."""
    backend_dir = Path(__file__).resolve().parent
    cmd = [sys.executable, "scripts/db_upgrade.py"]
    print(f"Auto-upgrade enabled. Running: {' '.join(cmd)}")
    completed = subprocess.run(cmd, cwd=str(backend_dir))
    if completed.returncode != 0:
        raise RuntimeError("Auto-upgrade failed. Fix migration errors and retry.")


def wipe_seed_tables() -> None:
    """Delete seeded content in FK-safe order (keeps migration history tables intact)."""
    db.session.query(RefreshToken).delete()
    db.session.query(RefreshTokenFamily).delete()
    db.session.query(RevokedToken).delete()
    db.session.query(Submissions).delete()
    db.session.query(UserPreferredHechshers).delete()
    db.session.query(PlaceHechshers).delete()
    db.session.query(PlaceTags).delete()
    db.session.query(PlaceAliases).delete()
    db.session.query(HechsherAliases).delete()
    db.session.query(Places).delete()
    db.session.query(Hechshers).delete()
    db.session.query(Users).delete()
    db.session.commit()


def has_seed_data() -> bool:
    return Users.query.count() > 0 or Places.query.count() > 0 or Hechshers.query.count() > 0


def seed_data() -> None:
    # --- Users (4 basic + 1 admin)
    users = {
        "admin": Users(user_email="admin@mapah.local", user_name="admin", user_status="admin"),
        "yael": Users(user_email="yael@mapah.local", user_name="yael", user_status="basic"),
        "david": Users(user_email="david@mapah.local", user_name="david", user_status="basic"),
        "sarah": Users(user_email="sarah@mapah.local", user_name="sarah", user_status="basic"),
        "moshe": Users(user_email="moshe@mapah.local", user_name="moshe", user_status="basic"),
    }
    user_passwords = {
        "admin": "AdminPass123!",
        "yael": "YaelPass123!",
        "david": "DavidPass123!",
        "sarah": "SarahPass123!",
        "moshe": "MoshePass123!",
    }
    for key, user in users.items():
        user.set_password(user_passwords[key])
    db.session.add_all(list(users.values()))
    db.session.flush()

    # --- Hechshers + aliases (Israel in Hebrew, NY in English)
    hechsher_specs = {
        # Israeli hechshers
        "rabanut_jerusalem": ("רבנות ירושלים", "/icons/rabanut_jerusalem.png", ["Jerusalem Rabbinate", "Jerusalem Rabbanut"]),
        "rabanut_tlv": ("רבנות תל אביב", "/icons/rabanut_tlv.png", ["Tel Aviv Rabbinate", "Tel Aviv Rabbanut"]),
        "rabanut_haifa": ("רבנות חיפה", "/icons/rabanut_haifa.png", ["Haifa Rabbinate"]),
        "rabanut_beer_sheva": ("רבנות באר שבע", "/icons/rabanut_beer_sheva.png", ["Beer Sheva Rabbinate"]),
        "badatz_eda": ("בד\"ץ העדה החרדית", "/icons/badatz_eda.png", ["Badatz", "Eda Haredit"]),
        "landau": ("הרב לנדא", "/icons/landau.png", ["Rav Landau", "Landau"]),
        "sheerit": ("שארית ישראל", "/icons/sheerit.png", ["Sheerit Yisrael"]),
        "beit_yosef": ("מהדרין בית יוסף", "/icons/beit_yosef.png", ["Beit Yosef", "Mehadrin Beit Yosef"]),
        "tzohar": ("צהר", "/icons/tzohar.png", ["Tzohar"]),
        "rubin": ("רובין", "/icons/rubin.png", ["Rubin"]),
        "mahpud": ("בד\"ץ יורה דעה הרב מחפוד", "/icons/mahpud.png", ["Machpud", "Mahpud"]),
        "petah_tikva_rabanut": ("רבנות פתח תקווה", "/icons/rabanut_pt.png", ["Petah Tikva Rabbinate"]),
        # American hechshers
        "ou": ("OU Kosher", "/icons/ou.png", ["OU", "Orthodox Union"]),
        "ok": ("OK Kosher", "/icons/ok.png", ["OK"]),
        "kofk": ("Kof-K", "/icons/kofk.png", ["Kof K"]),
        "stark": ("Star-K", "/icons/stark.png", ["Star K"]),
        "crc": ("cRc", "/icons/crc.png", ["CRC", "Chicago Rabbinical Council"]),
        "trianglek": ("Triangle K", "/icons/trianglek.png", ["TriangleK"]),
        "scrollk": ("Scroll K", "/icons/scrollk.png", ["ScrollK"]),
        "earthkosher": ("EarthKosher", "/icons/earthkosher.png", ["Earth Kosher"]),
        "tabletk": ("Tablet-K", "/icons/tabletk.png", ["Tablet K"]),
        "queens_vaad": ("Queens Vaad", "/icons/queens_vaad.png", ["KVH", "Vaad Harabonim of Queens"]),
    }

    hechshers = {}
    for key, (display_name, symbol, aliases) in hechsher_specs.items():
        hechsher = Hechshers(hechsher_display_name=display_name, hechsher_symbol=symbol)
        db.session.add(hechsher)
        hechshers[key] = hechsher
    db.session.flush()

    for key, (_, _, aliases) in hechsher_specs.items():
        for alias in aliases:
            db.session.add(
                HechsherAliases(
                    hechsher_id=hechshers[key].hechsher_id,
                    hechsher_alias=alias,
                )
            )

    # --- Preferences
    user_preferences = {
        "yael": ["badatz_eda", "beit_yosef", "landau"],
        "david": ["rabanut_tlv", "tzohar"],
        "sarah": ["ou", "stark", "queens_vaad"],
        "moshe": ["kofk", "ok", "crc"],
    }
    for user_key, hechsher_keys in user_preferences.items():
        for hechsher_key in hechsher_keys:
            db.session.add(
                UserPreferredHechshers(
                    user_id=users[user_key].user_id,
                    hechsher_id=hechshers[hechsher_key].hechsher_id,
                )
            )

    # --- Place generation (100+ places across Israel + New York)
    places = {}
    place_meta = {}

    israel_city_specs = [
        ("tel_aviv", "תל אביב", "Tel Aviv", 32.0853, 34.7818),
        ("jerusalem", "ירושלים", "Jerusalem", 31.7683, 35.2137),
        ("haifa", "חיפה", "Haifa", 32.7940, 34.9896),
        ("beer_sheva", "באר שבע", "Beer Sheva", 31.2518, 34.7913),
        ("bnei_brak", "בני ברק", "Bnei Brak", 32.0840, 34.8350),
        ("netanya", "נתניה", "Netanya", 32.3215, 34.8532),
        ("ashdod", "אשדוד", "Ashdod", 31.8014, 34.6435),
        ("raanana", "רעננה", "Raanana", 32.1848, 34.8713),
        ("petah_tikva", "פתח תקווה", "Petah Tikva", 32.0840, 34.8878),
        ("tiberias", "טבריה", "Tiberias", 32.7922, 35.5312),
        ("eilat", "אילת", "Eilat", 29.5577, 34.9519),
        ("rishon", "ראשון לציון", "Rishon LeZion", 31.9710, 34.7894),
    ]
    israel_templates = [
        ("גריל", "Grill", ["restaurant", "meat"]),
        ("קפה", "Cafe", ["cafe", "dairy"]),
        ("מאפיית", "Bakery", ["bakery", "parve"]),
        ("מרקט", "Market", ["store", "parve"]),
        ("חומוס", "Hummus", ["restaurant", "parve"]),
    ]
    israeli_hechsher_keys = [
        "rabanut_jerusalem",
        "rabanut_tlv",
        "rabanut_haifa",
        "rabanut_beer_sheva",
        "badatz_eda",
        "landau",
        "sheerit",
        "beit_yosef",
        "tzohar",
        "rubin",
        "mahpud",
        "petah_tikva_rabanut",
    ]

    street_numbers = [7, 12, 18, 26, 33]
    hebrew_streets = ["הרצל", "אלנבי", "ביאליק", "יפו", "הנביאים"]
    english_street_aliases = ["Herzl", "Allenby", "Bialik", "Jaffa", "HaNeviim"]

    place_counter = 0
    for city_idx, (city_key, city_he, city_en, base_lat, base_lng) in enumerate(israel_city_specs):
        for template_idx, (name_he, alias_en, tags) in enumerate(israel_templates):
            key = f"isr_{city_key}_{template_idx}"
            place = Places(
                place_name=f"{name_he} {city_he}",
                street_address=f"{hebrew_streets[template_idx]} {street_numbers[template_idx]}, {city_he}",
                latitude=round(base_lat + (template_idx * 0.004) + (city_idx * 0.0003), 7),
                longitude=round(base_lng + (template_idx * 0.004) + (city_idx * 0.0002), 7),
                is_active=True,
            )
            db.session.add(place)
            places[key] = place
            place_meta[key] = {
                "region": "israel",
                "tags": tags,
                "aliases": [f"{city_en} {alias_en}", f"{english_street_aliases[template_idx]} {city_en}"],
                "hechsher_keys": [
                    israeli_hechsher_keys[(place_counter + template_idx) % len(israeli_hechsher_keys)],
                    israeli_hechsher_keys[(place_counter + template_idx + 3) % len(israeli_hechsher_keys)],
                ] if template_idx in (0, 2) else [
                    israeli_hechsher_keys[(place_counter + template_idx) % len(israeli_hechsher_keys)]
                ],
            }
            place_counter += 1

    ny_area_specs = [
        ("manhattan", "Manhattan", 40.7831, -73.9712),
        ("brooklyn", "Brooklyn", 40.6782, -73.9442),
        ("queens", "Queens", 40.7282, -73.7949),
        ("bronx", "Bronx", 40.8448, -73.8648),
        ("staten_island", "Staten Island", 40.5795, -74.1502),
    ]
    ny_templates = [
        ("Central Grill", ["restaurant", "meat"]),
        ("Corner Cafe", ["cafe", "dairy"]),
        ("Artisan Bakery", ["bakery", "parve"]),
        ("Kosher Market", ["store", "parve"]),
        ("Deli House", ["store", "meat"]),
        ("Falafel Spot", ["restaurant", "parve"]),
        ("Pizza House", ["restaurant", "dairy"]),
        ("Bagel Corner", ["bakery", "dairy"]),
        ("Sushi Express", ["restaurant", "parve"]),
    ]
    american_hechsher_keys = [
        "ou",
        "ok",
        "kofk",
        "stark",
        "crc",
        "trianglek",
        "scrollk",
        "earthkosher",
        "tabletk",
        "queens_vaad",
    ]
    ny_streets = [
        "Lexington Ave",
        "Ocean Parkway",
        "Main Street",
        "Grand Concourse",
        "Hylan Boulevard",
        "Kings Highway",
        "Queens Blvd",
        "Flatbush Ave",
        "Broadway",
    ]

    for area_idx, (area_key, area_name, base_lat, base_lng) in enumerate(ny_area_specs):
        for template_idx, (name_en, tags) in enumerate(ny_templates):
            key = f"ny_{area_key}_{template_idx}"
            place = Places(
                place_name=f"{area_name} {name_en}",
                street_address=f"{100 + template_idx * 17} {ny_streets[template_idx]}, {area_name}, NY",
                latitude=round(base_lat + (template_idx * 0.005) + (area_idx * 0.0004), 7),
                longitude=round(base_lng + (template_idx * 0.005) + (area_idx * 0.0003), 7),
                is_active=True,
            )
            db.session.add(place)
            places[key] = place
            place_meta[key] = {
                "region": "new_york",
                "tags": tags,
                "aliases": [f"{area_name} {name_en.split()[0]}"] if template_idx % 2 == 0 else [],
                "hechsher_keys": [
                    american_hechsher_keys[(area_idx + template_idx) % len(american_hechsher_keys)],
                    american_hechsher_keys[(area_idx + template_idx + 2) % len(american_hechsher_keys)],
                ] if template_idx in (0, 3, 7) else [
                    american_hechsher_keys[(area_idx + template_idx) % len(american_hechsher_keys)]
                ],
            }

    # --- Manual edge cases
    edge_place_specs = {
        "isr_duplicate_a": ("קפה המרכז", "בן יהודה 44, תל אביב", 32.0781, 34.7692, True),
        "isr_duplicate_b": ("קפה המרכז", "בן מימון 11, ירושלים", 31.7755, 35.2111, True),
        "ny_duplicate_a": ("Central Deli", "550 Kingston Ave, Brooklyn, NY", 40.6681, -73.9426, True),
        "ny_duplicate_b": ("Central Deli", "212 Grand St, Manhattan, NY", 40.7162, -73.9911, True),
        "inactive_israel": ("המסעדה הישנה", "שוק הפשפשים 15, יפו", 32.0548, 34.7528, False),
        "inactive_ny": ("Closed Kosher Corner", "91 Delancey St, Manhattan, NY", 40.7187, -73.9890, False),
        "no_coords_israel": ("חומוס ללא מיקום", "יהודה הלוי 21, תל אביב", None, None, True),
        "no_coords_ny": ("Mystery Bakery", "74 Lee Ave, Brooklyn, NY", None, None, True),
        "no_tags_israel": ("מטבח השף", "דרך חברון 88, ירושלים", 31.7463, 35.2227, True),
        "no_hechsher_israel": ("ירקנייה שכונתית", "ויצמן 33, כפר סבא", 32.1750, 34.9070, True),
    }
    for key, (name, address, lat, lng, is_active) in edge_place_specs.items():
        place = Places(
            place_name=name,
            street_address=address,
            latitude=lat,
            longitude=lng,
            is_active=is_active,
        )
        db.session.add(place)
        places[key] = place

    db.session.flush()

    # Populate tags / aliases / hechshers for generated places.
    for key, meta in place_meta.items():
        for alias in meta["aliases"]:
            db.session.add(PlaceAliases(place_id=places[key].place_id, place_alias=alias))
        for tag in meta["tags"]:
            db.session.add(PlaceTags(place_id=places[key].place_id, place_tag=tag))
        for idx, hechsher_key in enumerate(meta["hechsher_keys"]):
            db.session.add(
                PlaceHechshers(
                    place_id=places[key].place_id,
                    hechsher_id=hechshers[hechsher_key].hechsher_id,
                    place_hechsher_marking_verity="verified" if idx == 0 else "pending",
                )
            )

    # Edge-case aliases/tags/hechshers
    edge_meta = {
        "isr_duplicate_a": {"aliases": ["Central Cafe Tel Aviv"], "tags": ["cafe", "dairy"], "hechshers": ["rabanut_tlv"]},
        "isr_duplicate_b": {"aliases": ["Central Cafe Jerusalem"], "tags": ["cafe", "parve"], "hechshers": ["rabanut_jerusalem"]},
        "ny_duplicate_a": {"aliases": ["BK Central Deli"], "tags": ["store", "meat"], "hechshers": ["ok", "kofk"]},
        "ny_duplicate_b": {"aliases": ["Manhattan Central Deli"], "tags": ["store", "meat"], "hechshers": ["ou"]},
        "inactive_israel": {"aliases": ["Old Restaurant Jaffa"], "tags": ["restaurant", "meat"], "hechshers": ["rabanut_tlv"]},
        "inactive_ny": {"aliases": ["Closed Corner"], "tags": ["store", "parve"], "hechshers": ["queens_vaad"]},
        "no_coords_israel": {"aliases": ["No Location Hummus"], "tags": ["restaurant", "parve"], "hechshers": ["badatz_eda"]},
        "no_coords_ny": {"aliases": ["Unknown Bakery"], "tags": ["bakery", "dairy"], "hechshers": ["stark"]},
        "no_tags_israel": {"aliases": ["Chef Kitchen Jerusalem"], "tags": [], "hechshers": ["beit_yosef"]},
        "no_hechsher_israel": {"aliases": ["Neighborhood Produce"], "tags": ["store", "parve"], "hechshers": []},
    }
    for key, meta in edge_meta.items():
        for alias in meta["aliases"]:
            db.session.add(PlaceAliases(place_id=places[key].place_id, place_alias=alias))
        for tag in meta["tags"]:
            db.session.add(PlaceTags(place_id=places[key].place_id, place_tag=tag))
        for idx, hechsher_key in enumerate(meta["hechshers"]):
            db.session.add(
                PlaceHechshers(
                    place_id=places[key].place_id,
                    hechsher_id=hechshers[hechsher_key].hechsher_id,
                    place_hechsher_marking_verity="verified" if idx == 0 else "pending",
                )
            )

    # --- Moderation history / uploads by users and admin
    visible_now = datetime.now(timezone.utc)
    uploaded_place_keys = [
        ("yael", "isr_tel_aviv_0", "approved", "approved"),
        ("david", "isr_jerusalem_1", "approved", "approved"),
        ("sarah", "ny_brooklyn_2", "approved", "pending_review"),
        ("moshe", "ny_queens_0", "approved", "approved"),
        ("admin", "isr_haifa_3", "approved", "approved"),
        ("admin", "ny_manhattan_4", "approved", "approved"),
        ("yael", "no_coords_israel", "flagged", "pending_review"),
        ("david", "inactive_israel", "flagged", "rejected"),
    ]
    for uploader_key, place_key, spam_result, admin_status in uploaded_place_keys:
        payload = {
            "submission_type": "new_place",
            "place_id": places[place_key].place_id,
            "place_name": places[place_key].place_name,
            "street_address": places[place_key].street_address,
            "latitude": float(places[place_key].latitude) if places[place_key].latitude is not None else None,
            "longitude": float(places[place_key].longitude) if places[place_key].longitude is not None else None,
            "hechsher_ids": [ph.hechsher_id for ph in places[place_key].place_hechshers],
            "tags": [pt.place_tag for pt in places[place_key].place_tags],
            "aliases": [pa.place_alias for pa in places[place_key].place_aliases],
            "source": "manual",
            "moderation": {"source": "seed", "reason": "seeded history"},
        }
        is_visible = spam_result == "approved" or admin_status == "approved"
        if admin_status == "rejected":
            is_visible = False
        db.session.add(
            Submissions(
                submitted_by_user_id=users[uploader_key].user_id,
                place_id=places[place_key].place_id,
                submission_type="new_place",
                payload_json=payload,
                spam_filter_result=spam_result,
                admin_review_status=admin_status,
                admin_reject_reason="Quality issue" if admin_status == "rejected" else None,
                is_visible=is_visible,
                published_at=visible_now if is_visible else None,
            )
        )

    extra_submissions = [
        {
            "user": "yael",
            "place": "isr_tel_aviv_1",
            "type": "alias_update",
            "spam": "approved",
            "admin": "approved",
            "payload": {
                "submission_type": "alias_update",
                "place_id": None,
                "aliases": ["Tel Aviv Coffee House", "Allenby Cafe"],
                "reason": "Common English names",
            },
        },
        {
            "user": "sarah",
            "place": "ny_brooklyn_6",
            "type": "edit",
            "spam": "flagged",
            "admin": "pending_review",
            "payload": {
                "submission_type": "edit",
                "place_name": "Brooklyn Pizza House Late Night",
                "changes": {"hours": "Open until midnight"},
                "reason": "Updated info",
            },
        },
        {
            "user": "moshe",
            "place": "isr_haifa_2",
            "type": "tag_update",
            "spam": "approved",
            "admin": "approved",
            "payload": {
                "submission_type": "tag_update",
                "tags": ["bakery", "parve"],
                "reason": "Confirmed pareve only",
            },
        },
        {
            "user": "admin",
            "place": None,
            "type": "hechsher_create",
            "spam": "flagged",
            "admin": "pending_review",
            "payload": {
                "submission_type": "hechsher_create",
                "hechsher": {
                    "hechsher_display_name": "Community Kashrus NYC",
                    "aliases": ["CKNYC", "Community Kashrus"],
                },
                "reason": "Proposed new regional certification",
            },
        },
        {
            "user": "david",
            "place": None,
            "type": "hechsher_create",
            "spam": "approved",
            "admin": "rejected",
            "payload": {
                "submission_type": "hechsher_create",
                "hechsher": {
                    "hechsher_display_name": "כשרות שכונתית",
                    "aliases": ["Neighborhood Kashrus"],
                },
                "reason": "Needs manual verification",
            },
        },
    ]
    for item in extra_submissions:
        place_id = places[item["place"]].place_id if item["place"] else None
        payload = dict(item["payload"])
        if place_id is not None:
            payload["place_id"] = place_id
        is_visible = item["spam"] == "approved" or item["admin"] == "approved"
        if item["admin"] == "rejected":
            is_visible = False
        db.session.add(
            Submissions(
                submitted_by_user_id=users[item["user"]].user_id,
                place_id=place_id,
                submission_type=item["type"],
                payload_json=payload,
                spam_filter_result=item["spam"],
                admin_review_status=item["admin"],
                admin_reject_reason="Rejected by seed scenario" if item["admin"] == "rejected" else None,
                is_visible=is_visible,
                published_at=visible_now if is_visible else None,
            )
        )

    db.session.commit()

    print("Seed complete.")
    print(f"Users seeded: {Users.query.count()} (basic: 4, admin: 1)")
    print(f"Hechshers seeded: {Hechshers.query.count()}")
    print(f"Places seeded: {Places.query.count()}")
    print(f"Submissions seeded: {Submissions.query.count()}")
    print("Admin login: admin@mapah.local / AdminPass123!")
    print("Basic logins: yael@mapah.local, david@mapah.local, sarah@mapah.local, moshe@mapah.local")


def run_seed() -> None:
    with app.app_context():
        auto_upgrade_flag = "--auto-upgrade" in sys.argv

        if auto_upgrade_flag:
            auto_upgrade_schema()

        ensure_schema_ready()
        wipe_flag = "--wipe" in sys.argv

        if wipe_flag:
            wipe_seed_tables()
            print("Wiped seedable tables.")

        if wipe_flag or not has_seed_data():
            seed_data()
        else:
            print("Existing data detected. Use --wipe to reseed.")


if __name__ == "__main__":
    run_seed()
