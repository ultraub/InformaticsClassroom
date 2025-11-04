from flask import Blueprint

auth_bp = Blueprint('auth_bp', __name__, template_folder='templates')

# Import routes to register them with the blueprint
from informatics_classroom.auth import routes
from informatics_classroom.auth import api_routes  # New API routes for React SPA