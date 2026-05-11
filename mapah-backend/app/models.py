from app import db
from sqlalchemy import Enum

# Enums from schema
place_tag_enum = Enum('restaurant', 'bakery', 'store', 'cafe', 'meat', 'dairy', 'parve', name='place_tag')
verification_status_enum = Enum('verified', 'pending', 'unverified', name='verification_status')
user_status_enum = Enum('admin', 'basic', name='user_status')

class Places(db.Model):
    __tablename__ = 'Places'
    PlaceId = db.Column(db.String(11), primary_key=True)
    PlaceName = db.Column(db.String(50), nullable=False)
    Coordinates = db.Column(db.String(50))
    StreetAddress = db.Column(db.String(255))
    DateAdded = db.Column(db.Date)

    def to_dict(self):
        return {
            'id': self.PlaceId,
            'name': self.PlaceName,
            'coordinates': self.Coordinates,
            'address': self.StreetAddress,
            'date_added': self.DateAdded.isoformat() if self.DateAdded else None
        }

class PlaceTags(db.Model):
    __tablename__ = 'PlaceTags'
    PlaceId = db.Column(db.String(11), db.ForeignKey('Places.PlaceId'), primary_key=True)
    PlaceTag = db.Column(place_tag_enum, primary_key=True)

class Hechshers(db.Model):
    __tablename__ = 'Hechshers'
    HechsherId = db.Column(db.String(11), primary_key=True)
    HechsherDisplayName = db.Column(db.String(50), nullable=False, unique=True)
    HechsherSymbol = db.Column(db.String(255))

class HechsherAliases(db.Model):
    __tablename__ = 'HechsherAliases'
    HechsherId = db.Column(db.String(11), db.ForeignKey('Hechshers.HechsherId'), primary_key=True)
    HechsherAlias = db.Column(db.String(50), primary_key=True)

class PlaceHechshers(db.Model):
    __tablename__ = 'PlaceHechshers'
    PlaceId = db.Column(db.String(11), db.ForeignKey('Places.PlaceId'), primary_key=True)
    HechsherId = db.Column(db.String(11), db.ForeignKey('Hechshers.HechsherId'), primary_key=True)
    PlaceHechsherMarkingVerity = db.Column(verification_status_enum)

class User(db.Model):
    __tablename__ = 'Users'
    UserId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserEmail = db.Column(db.String(255), nullable=False)
    UserName = db.Column(db.String(50), nullable=False)
    UserPassword = db.Column(db.String(256), nullable=False)
    UserStatus = db.Column(user_status_enum, default='basic')
    UserSinceDate = db.Column(db.DateTime(timezone=True), default=db.func.now())
