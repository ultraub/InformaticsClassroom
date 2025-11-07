from flask import Blueprint

classroom_bp=Blueprint('classroom_bp',__name__, template_folder='templates', static_folder='static')

# Import routes to register them with the blueprint
from informatics_classroom.classroom import routes
from informatics_classroom.classroom import api_routes  # New API routes for React SPA
