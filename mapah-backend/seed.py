import sys
from datetime import datetime, UTC

from app import create_app, db
from app.models import (
    Users,
    Places,
    Hechshers,
    HechsherAliases,
    PlaceTags,
    PlaceHechshers
)

app = create_app()

def tables_are_empty():
    return (
        Users.query.count() == 0 and
        Places.query.count() == 0 and
        Hechshers.query.count() == 0 and
        HechsherAliases.query.count() == 0 and
        PlaceTags.query.count() == 0 and
        PlaceHechshers.query.count() == 0
    )

def wipe_tables():
    db.session.query(PlaceHechshers).delete()
    db.session.query(PlaceTags).delete()
    db.session.query(HechsherAliases).delete()
    db.session.query(Hechshers).delete()
    db.session.query(Places).delete()
    db.session.query(Users).delete()
    db.session.commit()
    print("🧹 Wiped all tables")

def seed_data():
    # -------------------------
    # USERS
    # -------------------------
    user1 = Users(
        user_email="yael@example.com",
        user_name="Yael",
        user_password="hashed_pw_yael",
        user_status="basic",
        user_since_date=datetime.now(UTC)
    )

    user2 = Users(
        user_email="david@example.com",
        user_name="David",
        user_password="hashed_pw_david",
        user_status="admin",
        user_since_date=datetime.now(UTC)
    )

    db.session.add_all([user1, user2])
    db.session.commit()

    # -------------------------
    # HECHSHERS (with edge cases)
    # -------------------------
    hech_rabbinate = Hechshers(
        hechsher_display_name="הרבנות הראשית לישראל",
        hechsher_symbol="rabbinate.png"
    )

    hech_badatz = Hechshers(
        hechsher_display_name='בד"ץ העדה החרדית',
        hechsher_symbol="badatz.png"
    )

    hech_tuv = Hechshers(
        hechsher_display_name="טוב הארץ",
        hechsher_symbol="tuvhaaretz.png"
    )

    hech_no_alias = Hechshers(
        hechsher_display_name="כשרות מהדרין מודיעין",
        hechsher_symbol=None
    )

    db.session.add_all([hech_rabbinate, hech_badatz, hech_tuv, hech_no_alias])
    db.session.commit()

    # Aliases (multiple, one, none)
    db.session.add_all([
        HechsherAliases(hechsher_id=hech_rabbinate.hechsher_id, hechsher_alias="Rabbinate"),
        HechsherAliases(hechsher_id=hech_rabbinate.hechsher_id, hechsher_alias="Rabbanut"),
        HechsherAliases(hechsher_id=hech_badatz.hechsher_id, hechsher_alias="Badatz Eda"),
        HechsherAliases(hechsher_id=hech_tuv.hechsher_id, hechsher_alias="Tuv HaAretz"),
        # hech_no_alias intentionally gets none
    ])
    db.session.commit()

    # -------------------------
    # PLACES (with edge cases)
    # -------------------------
    place_multi_tags = Places(
        place_name="Falafel HaKosem",
        coordinates="32.0700,34.7760",
        street_address="Shlomo HaMelech 1, Tel Aviv",
        date_added=datetime.now(UTC)
    )

    place_one_tag = Places(
        place_name="Machneyuda",
        coordinates="31.7834,35.2160",
        street_address="Beit Yaakov 10, Jerusalem",
        date_added=datetime.now(UTC)
    )

    place_no_tags = Places(
        place_name="Shawarma Hazan",
        coordinates="32.7940,34.9896",
        street_address="Herzl 45, Haifa",
        date_added=datetime.now(UTC)
    )

    place_multi_hechsher = Places(
        place_name="Café Aroma Mehadrin",
        coordinates="31.7710,35.2170",
        street_address="Jaffa St 99, Jerusalem",
        date_added=datetime.now(UTC)
    )

    place_no_hechsher = Places(
        place_name="Hipster Vegan TLV",
        coordinates="32.0800,34.7800",
        street_address="Dizengoff 200, Tel Aviv",
        date_added=datetime.now(UTC)
    )

    db.session.add_all([
        place_multi_tags,
        place_one_tag,
        place_no_tags,
        place_multi_hechsher,
        place_no_hechsher
    ])
    db.session.commit()

    # -------------------------
    # TAGS (using your ENUM place_tag)
    # -------------------------
    db.session.add_all([
        # multiple tags
        PlaceTags(place_id=place_multi_tags.place_id, place_tag="restaurant"),
        PlaceTags(place_id=place_multi_tags.place_id, place_tag="meat"),
        PlaceTags(place_id=place_multi_tags.place_id, place_tag="parve"),

        # one tag
        PlaceTags(place_id=place_one_tag.place_id, place_tag="restaurant"),

        # no tags → place_no_tags gets none
    ])
    db.session.commit()

    # -------------------------
    # PLACE ↔ HECHSHER RELATIONSHIPS (using your ENUM verification_status)
    # -------------------------
    db.session.add_all([
        PlaceHechshers(
            place_id=place_multi_tags.place_id,
            hechsher_id=hech_rabbinate.hechsher_id,
            place_hechsher_marking_verity="verified"
        ),
        PlaceHechshers(
            place_id=place_one_tag.place_id,
            hechsher_id=hech_badatz.hechsher_id,
            place_hechsher_marking_verity="verified"
        ),
        PlaceHechshers(
            place_id=place_no_tags.place_id,
            hechsher_id=hech_tuv.hechsher_id,
            place_hechsher_marking_verity="unverified"
        ),
        # multi-hechsher place
        PlaceHechshers(
            place_id=place_multi_hechsher.place_id,
            hechsher_id=hech_rabbinate.hechsher_id,
            place_hechsher_marking_verity="verified"
        ),
        PlaceHechshers(
            place_id=place_multi_hechsher.place_id,
            hechsher_id=hech_badatz.hechsher_id,
            place_hechsher_marking_verity="pending"
        ),
        # no-hechsher place → none added
    ])
    db.session.commit()

    print("🌱 Seeded Israeli test data with ENUMs + edge cases successfully!")

def run_seed():
    with app.app_context():
        wipe_flag = "--wipe" in sys.argv

        if wipe_flag:
            wipe_tables()
            seed_data()
            return

        if tables_are_empty():
            print("📭 Tables empty — seeding fresh data")
            seed_data()
        else:
            print("📦 Tables already contain data — skipping seeding")
            print("Run with --wipe to force a reset")

if __name__ == "__main__":
    run_seed()
