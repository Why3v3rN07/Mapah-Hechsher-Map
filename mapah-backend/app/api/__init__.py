from flask import Blueprint

api_bp = Blueprint("api", __name__)

from . import places, hechshers, submissions, me, admin  # noqa: E402, F401

