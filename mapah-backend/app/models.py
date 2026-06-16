from app import db
from sqlalchemy import Enum

# Enums from schema
place_tag_enum = Enum('restaurant', 'bakery', 'store', 'cafe', 'meat', 'dairy', 'parve', name='place_tag')
verification_status_enum = Enum('verified', 'pending', 'unverified', name='verification_status')
user_status_enum = Enum('admin', 'basic', name='user_status')


class Places(db.Model):
    __tablename__ = 'places'
    place_id = db.Column(db.Integer, primary_key=True)
    place_name = db.Column(db.String(50), nullable=False)
    coordinates = db.Column(db.String(50))
    street_address = db.Column(db.String(255))
    date_added = db.Column(db.Date)

    def to_dict(self):
        return {
            'id': self.place_id,
            'name': self.place_name,
            'coordinates': self.coordinates,
            'address': self.street_address,
            'date_added': self.date_added.isoformat() if self.date_added else None
        }


class PlaceTags(db.Model):
    __tablename__ = 'place_tags'
    place_id = db.Column(db.String(11), db.ForeignKey('places.place_id'), primary_key=True)
    place_tag = db.Column(place_tag_enum, primary_key=True)


class Hechshers(db.Model):
    __tablename__ = 'hechshers'
    hechsher_id = db.Column(db.Integer, primary_key=True)
    hechsher_display_name = db.Column(db.String(50), nullable=False, unique=True)
    hechsher_symbol = db.Column(db.String(255))


class HechsherAliases(db.Model):
    __tablename__ = 'hechsher_aliases'
    hechsher_id = db.Column(db.String(11), db.ForeignKey('hechshers.hechsher_id'), primary_key=True)
    hechsher_alias = db.Column(db.String(50), primary_key=True)


class PlaceHechshers(db.Model):
    __tablename__ = 'place_hechshers'
    place_id = db.Column(db.Integer, db.ForeignKey('places.place_id'), primary_key=True)
    hechsher_id = db.Column(db.Integer, db.ForeignKey('hechshers.hechsher_id'), primary_key=True)
    place_hechsher_marking_verity = db.Column(verification_status_enum)


class Users(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_email = db.Column(db.String(255), nullable=False)
    user_name = db.Column(db.String(50), nullable=False)
    user_password = db.Column(db.String(256), nullable=False)
    user_status = db.Column(user_status_enum, default='basic')
    user_since_date = db.Column(db.DateTime(timezone=True), default=db.func.now())
