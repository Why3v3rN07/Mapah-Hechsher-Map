'''
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.config import Config

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)


@app.route('/')
def hello():
    return 'Hello, Mapah Backend!'

if __name__ == '__main__':
    app.run(debug=True)
'''
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from .extensions import db
from .models import Places, PlaceTags, PlaceHechshers

import uuid
from math import radians, sin, cos, sqrt, atan2

def haversine(lat1, lon1, lat2, lon2):
    R = 3958.8  # Earth radius in miles
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

main_bp = Blueprint("main_bp", __name__)


@main_bp.route("/")
def home():
    return {"message": "Welcome to Mapah"}

@main_bp.route("/places", methods=["GET"])
def get_places():
    places = Places.query.all()
    return jsonify([place.to_dict() for place in places])

@main_bp.route("/places/<id>", methods=["GET"])
def get_place(id):
    place = Places.query.get(id)
    if not place:
        return jsonify({"error": "Place not found"}), 404
    return jsonify(place.to_dict())

@main_bp.route("/places", methods=["POST"])
def get_places_within():
    data = request.get_json() or {}
    location = data.get('location')
    within = data.get('within')
    if not location or within is None:
        return jsonify({"error": "location and within are required"}), 400
    try:
        lat, lng = map(float, location.split(','))
        within = float(within)
    except ValueError:
        return jsonify({"error": "invalid location or within format"}), 400
    places = Places.query.all()
    result = []
    for place in places:
        if place.Coordinates:
            try:
                p_lat, p_lng = map(float, place.coordinates.split(','))
                dist = haversine(lat, lng, p_lat, p_lng)
                if dist <= within:
                    result.append(place.to_dict())
            except ValueError:
                pass
    return jsonify(result)

@main_bp.route("/places/add", methods=["POST"])
@login_required
def add_place():
    data = request.get_json() or {}
    name = data.get('name')
    hechsher = data.get('hechsher')
    address = data.get('address')
    coordinates = data.get('coordinates') #TODO - need to get this from ip
    tags = data.get('tags', [])
    if not name or not address or not coordinates:
        return jsonify({"error": "name, address, coordinates are required"}), 400
    place_id = str(uuid.uuid4())[:11].upper()
    place = Places(place_id=place_id, place_name=name, street_address=address, coordinates=coordinates, date_added=db.func.current_date())
    db.session.add(place)
    if hechsher:
        ph = PlaceHechshers(place_id=place_id, hechsher_id=hechsher)
        db.session.add(ph)
    for tag in tags:
        pt = PlaceTags(place_id=place_id, place_tag=tag)
        db.session.add(pt)
    try:
        db.session.commit()
        return jsonify(place.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
