import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone

from app import create_app
from app.extensions import db
from app.models import (
    HechsherAliases,
    Hechshers,
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
    db.session.query(HechsherAliases).delete()
    db.session.query(Places).delete()
    db.session.query(Hechshers).delete()
    db.session.query(Users).delete()
    db.session.commit()


def has_seed_data() -> bool:
    return Users.query.count() > 0 or Places.query.count() > 0 or Hechshers.query.count() > 0


def seed_data() -> None:
    # --- Users
    admin = Users(user_email="admin@mapah.local", user_name="admin", user_status="admin")
    admin.set_password("AdminPass123!")

    contributor = Users(
        user_email="contributor@mapah.local",
        user_name="contributor",
        user_status="basic",
    )
    contributor.set_password("ContributorPass123!")

    viewer = Users(user_email="viewer@mapah.local", user_name="viewer", user_status="basic")
    viewer.set_password("ViewerPass123!")

    db.session.add_all([admin, contributor, viewer])
    db.session.flush()

    # --- Hechshers + aliases
    hechshers = {
        "rabbinate_jerusalem": Hechshers(
            hechsher_display_name="רבנות ירושלים",
            hechsher_symbol="/icons/rabbinate_jerusalem.png",
        ),
        "badatz": Hechshers(
            hechsher_display_name="בד\"ץ העדה החרדית",
            hechsher_symbol="/icons/badatz.png",
        ),
        "tzohar": Hechshers(
            hechsher_display_name="צהר",
            hechsher_symbol="/icons/tzohar.png",
        ),
        "beit_yosef": Hechshers(
            hechsher_display_name="מהדרין בית יוסף",
            hechsher_symbol="/icons/beit_yosef.png",
        ),
        "tel_aviv_rabbinate": Hechshers(
            hechsher_display_name="רבנות תל אביב",
            hechsher_symbol="/icons/rabbinate_tlv.png",
        ),
    }

    db.session.add_all(list(hechshers.values()))
    db.session.flush()

    db.session.add_all(
        [
            HechsherAliases(hechsher_id=hechshers["rabbinate_jerusalem"].hechsher_id, hechsher_alias="Rabbanut Jerusalem"),
            HechsherAliases(hechsher_id=hechshers["rabbinate_jerusalem"].hechsher_id, hechsher_alias="Rabanut Jerusalem"),
            HechsherAliases(hechsher_id=hechshers["badatz"].hechsher_id, hechsher_alias="Badatz"),
            HechsherAliases(hechsher_id=hechshers["badatz"].hechsher_id, hechsher_alias="Eda Haredit"),
            HechsherAliases(hechsher_id=hechshers["tzohar"].hechsher_id, hechsher_alias="Tzohar"),
            HechsherAliases(hechsher_id=hechshers["beit_yosef"].hechsher_id, hechsher_alias="Mehadrin Beit Yosef"),
            HechsherAliases(hechsher_id=hechshers["tel_aviv_rabbinate"].hechsher_id, hechsher_alias="רבנות ת\"א"),
        ]
    )

    # --- Preferences
    db.session.add_all(
        [
            UserPreferredHechshers(user_id=contributor.user_id, hechsher_id=hechshers["badatz"].hechsher_id),
            UserPreferredHechshers(user_id=contributor.user_id, hechsher_id=hechshers["beit_yosef"].hechsher_id),
            UserPreferredHechshers(user_id=viewer.user_id, hechsher_id=hechshers["rabbinate_jerusalem"].hechsher_id),
        ]
    )

    # --- Places (Hebrew display names across multiple cities)
    # Edge cases included:
    # - duplicate display name in different cities
    # - inactive place
    # - place with no coordinates
    # - place with no tags
    # - place with no hechsher
    place_specs = {
        "falafel_hakosem": ("פלאפל הקוסם", "שלמה המלך 1, תל אביב", 32.0700, 34.7760, True),
        "machneyuda": ("מחניודה", "בית יעקב 10, ירושלים", 31.7834, 35.2160, True),
        "carmel_bakery": ("מאפיית הכרמל", "הרצל 45, חיפה", 32.7940, 34.9896, True),
        "neve_tzedek_cafe": ("קפה נווה צדק", "שבזי 30, תל אביב", 32.0629, 34.7686, True),
        "hatikva_shawarma": ("שווארמה התקווה", "דרך ההגנה 55, תל אביב", 32.0550, 34.7950, True),
        "yarkon_market": ("מרכז הירקון מרקט", "אבן גבירול 150, תל אביב", 32.0905, 34.7818, True),
        "geula_pastry": ("קונדיטוריית גאולה", "יפו 85, ירושלים", 31.7857, 35.2118, True),
        "carmel_deli": ("מעדניית הכרמל", "הנביאים 12, חיפה", 32.8150, 34.9980, True),
        "hagefen_cafe": ("בית קפה הגפן", "הנשיא 25, באר שבע", 31.2520, 34.7915, True),
        "old_city_bakery": ("מאפיית העיר העתיקה", "רחוב דוד 3, ירושלים", 31.7766, 35.2297, True),
        "eilat_fish": ("דגי אילת", "שדרות התמרים 9, אילת", 29.5581, 34.9482, True),
        "tiberias_grill": ("הגריל הטברייני", "הבנים 4, טבריה", 32.7922, 35.5312, True),
        "haifa_cafe_roman": ("קפה הכרמל", "שדרות מוריה 112, חיפה", 32.8008, 34.9851, True),
        "jerusalem_cafe_same_name": ("קפה הכרמל", "עמק רפאים 18, ירושלים", 31.7624, 35.2183, True),
        "bnei_brak_store": ("סופר ברכה", "רבי עקיבא 67, בני ברק", 32.0843, 34.8326, True),
        "inactive_place": ("המקום הישן", "שוק הפשפשים 15, יפו", 32.0548, 34.7528, False),
        "no_coords_place": ("חומוס הבית", "יהודה הלוי 21, תל אביב", None, None, True),
        "no_tags_place": ("מטבח השף", "דרך חברון 88, ירושלים", 31.7463, 35.2227, True),
        "no_hechsher_place": ("ירקנייה השכונתית", "ויצמן 33, כפר סבא", 32.1750, 34.9070, True),
    }

    places = {}
    for key, (name, address, lat, lng, is_active) in place_specs.items():
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

    # --- Place hechshers mapping
    place_hechsher_map = {
        "falafel_hakosem": ["badatz", "tel_aviv_rabbinate"],
        "machneyuda": ["rabbinate_jerusalem", "badatz"],
        "carmel_bakery": ["tzohar"],
        "neve_tzedek_cafe": ["tel_aviv_rabbinate"],
        "hatikva_shawarma": ["badatz", "beit_yosef"],
        "yarkon_market": ["tel_aviv_rabbinate"],
        "geula_pastry": ["rabbinate_jerusalem", "beit_yosef"],
        "carmel_deli": ["tzohar"],
        "hagefen_cafe": ["beit_yosef"],
        "old_city_bakery": ["rabbinate_jerusalem"],
        "eilat_fish": ["tzohar"],
        "tiberias_grill": ["rabbinate_jerusalem"],
        "haifa_cafe_roman": ["tzohar"],
        "jerusalem_cafe_same_name": ["rabbinate_jerusalem"],
        "bnei_brak_store": ["badatz"],
        "inactive_place": ["tel_aviv_rabbinate"],
        "no_coords_place": ["tel_aviv_rabbinate"],
        "no_tags_place": ["rabbinate_jerusalem"],
        # no_hechsher_place intentionally omitted
    }
    for place_key, hechsher_keys in place_hechsher_map.items():
        for key in hechsher_keys:
            db.session.add(
                PlaceHechshers(
                    place_id=places[place_key].place_id,
                    hechsher_id=hechshers[key].hechsher_id,
                    place_hechsher_marking_verity="verified",
                )
            )

    # --- Place tags mapping (for robust filter testing)
    place_tag_map = {
        "falafel_hakosem": ["restaurant", "meat"],
        "machneyuda": ["restaurant", "meat"],
        "carmel_bakery": ["bakery", "parve"],
        "neve_tzedek_cafe": ["cafe", "dairy"],
        "hatikva_shawarma": ["restaurant", "meat"],
        "yarkon_market": ["store", "parve"],
        "geula_pastry": ["bakery", "dairy"],
        "carmel_deli": ["store", "meat"],
        "hagefen_cafe": ["cafe", "parve"],
        "old_city_bakery": ["bakery", "parve"],
        "eilat_fish": ["restaurant", "meat"],
        "tiberias_grill": ["restaurant", "meat"],
        "haifa_cafe_roman": ["cafe", "dairy"],
        "jerusalem_cafe_same_name": ["cafe", "parve"],
        "bnei_brak_store": ["store", "parve"],
        "inactive_place": ["restaurant", "meat"],
        "no_coords_place": ["restaurant", "parve"],
        # no_tags_place intentionally omitted
        # no_hechsher_place intentionally omitted
    }
    for place_key, tags in place_tag_map.items():
        for tag in tags:
            db.session.add(PlaceTags(place_id=places[place_key].place_id, place_tag=tag))

    # --- Example moderation history rows
    db.session.add_all(
        [
            Submissions(
                submitted_by_user_id=contributor.user_id,
                place_id=places["falafel_hakosem"].place_id,
                submission_type="tag_update",
                payload_json={
                    "submission_type": "tag_update",
                    "place_id": places["falafel_hakosem"].place_id,
                    "tags": ["restaurant", "meat"],
                    "reason": "confirmed during visit",
                },
                spam_filter_result="approved",
                admin_review_status="approved",
                is_visible=True,
                published_at=datetime.now(timezone.utc),
            ),
            Submissions(
                submitted_by_user_id=viewer.user_id,
                place_id=places["machneyuda"].place_id,
                submission_type="tag_update",
                payload_json={
                    "submission_type": "tag_update",
                    "place_id": places["machneyuda"].place_id,
                    "tags": ["dairy", "cafe"],
                    "reason": "menu changed",
                },
                spam_filter_result="flagged",
                admin_review_status="pending_review",
                is_visible=False,
            ),
            Submissions(
                submitted_by_user_id=viewer.user_id,
                place_id=places["neve_tzedek_cafe"].place_id,
                submission_type="edit",
                payload_json={
                    "submission_type": "edit",
                    "place_id": places["neve_tzedek_cafe"].place_id,
                    "place_name": "קפה נווה צדק המחודש",
                    "tags": ["cafe", "dairy"],
                },
                spam_filter_result="approved",
                admin_review_status="pending_review",
                is_visible=True,
                published_at=datetime.now(timezone.utc),
            ),
        ]
    )

    db.session.commit()

    print("Seed complete.")
    print(f"Places seeded: {Places.query.count()}")
    print("Admin login: admin@mapah.local / AdminPass123!")
    print("Contributor login: contributor@mapah.local / ContributorPass123!")


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
