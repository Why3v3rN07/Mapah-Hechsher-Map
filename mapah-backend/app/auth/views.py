from flask import request, jsonify
from flask_login import login_user, logout_user, login_required

from app.extensions import db
from app.models import User
from . import auth_bp


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    # Basic validation
    if not username or not email or not password:
        return jsonify({"error": "username, email and password are required"}), 400

    if len(password) < 8:
        return jsonify({"error": "password must be at least 8 characters"}), 400

    # Check for duplicates
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "username already taken"}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "email already registered"}), 409

    # Create user — password setter calls generate_password_hash internally
    user = User(username=username, email=email)
    user.password = password
    db.session.add(user)
    db.session.commit()

    return jsonify(user.to_dict()), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data     = request.get_json() or {}
    username = data.get("username", "")
    password = data.get("password", "")

    user = User.query.filter_by(username=username).first()

    if user is None or not user.verify_password(password):
        # Same error for both cases — don't hint which field was wrong
        return jsonify({"error": "invalid username or password"}), 401

    remember = data.get("remember_me", False)
    login_user(user, remember=remember)
    return jsonify(user.to_dict()), 200


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "logged out"}), 200

