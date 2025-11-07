from flask import Flask, session, url_for, send_from_directory, jsonify
from flask_session import Session
from flask_cors import CORS
from informatics_classroom.config import Config
import msal
import os

from informatics_classroom.classroom.routes import classroom_bp
from informatics_classroom.imageupload.routes import image_bp
from informatics_classroom.networkbuilder.routes import network_bp
from informatics_classroom.mlmodelgame.routes import mlmodel_bp
from informatics_classroom.auth.routes import auth_bp, auth_configure_app


def create_app():
    app=Flask(__name__)
    app=auth_configure_app(app)

    # Enable CORS for development (allows localhost and 127.0.0.1)
    CORS(app,
         resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"]}},
         supports_credentials=True,
         allow_headers=['Content-Type', 'Authorization'],
         methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
    )

    # Register all API blueprints with /api prefix (for backward compatibility, also register at /)
    app.register_blueprint(classroom_bp,url_prefix='/')
    app.register_blueprint(image_bp,url_prefix='/')
    app.register_blueprint(network_bp,url_prefix='/')
    app.register_blueprint(mlmodel_bp,url_prefix='/')
    app.register_blueprint(auth_bp,url_prefix='/')

    # ========== REACT SPA SERVING ==========

    # Serve React static files
    @app.route('/assets/<path:filename>')
    def serve_react_assets(filename):
        """Serve React build assets (CSS, JS, images)"""
        return send_from_directory(
            os.path.join(Config.REACT_BUILD_PATH, 'assets'),
            filename
        )

    # Health check endpoint for React app
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Simple health check for the API"""
        return jsonify({
            'status': 'healthy',
            'react_ui_enabled': Config.USE_REACT_UI,
            'rollout_mode': Config.REACT_ROLLOUT_MODE
        }), 200

    # Catch-all route to serve React SPA for non-API routes
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_react_spa(path):
        """
        Serve React SPA for all non-API routes.
        This must be the LAST route registered to act as a fallback.
        """
        # Don't intercept API routes - let blueprints handle them
        if path.startswith('api/'):
            return jsonify({'error': 'API endpoint not found'}), 404

        # Check if React UI is enabled
        if not Config.USE_REACT_UI:
            return jsonify({
                'error': 'React UI is disabled',
                'message': 'Set USE_REACT_UI=true in .env to enable React frontend'
            }), 503

        # Check if React build directory exists
        if not os.path.exists(Config.REACT_BUILD_PATH):
            return jsonify({
                'error': 'React build not found',
                'message': f'Build directory does not exist: {Config.REACT_BUILD_PATH}',
                'hint': 'Run: cd informatics-classroom-ui && npm run build'
            }), 503

        # Check if user is authenticated and has required role for React UI
        user_roles = session.get('user', {}).get('roles', [])
        if not any(role in Config.REACT_ENABLED_ROLES for role in user_roles):
            # User doesn't have access to React UI yet
            # For now, serve React anyway (login page will handle this)
            # In production, you might want to redirect to a "coming soon" page
            pass

        # Serve index.html for all routes (React Router handles client-side routing)
        return send_from_directory(Config.REACT_BUILD_PATH, 'index.html')

    return app

def _load_cache():
    cache = msal.SerializableTokenCache()
    if session.get("token_cache"):
        cache.deserialize(session["token_cache"])
    return cache

def _save_cache(cache):
    if cache.has_state_changed:
        session["token_cache"] = cache.serialize()

def _build_msal_app(cache=None, authority=None):
    return msal.ConfidentialClientApplication(
        Config.CLIENT_ID, authority=authority or Config.AUTHORITY,
        client_credential=Config.CLIENT_SECRET, token_cache=cache)

def _build_auth_code_flow(authority=None, scopes=None):
    return _build_msal_app(authority=authority).initiate_auth_code_flow(
        scopes or [],
        redirect_uri=url_for("authorized", _external=True))

def _get_token_from_cache(scope=None):
    cache = _load_cache()  # This web app maintains one cache per session
    cca = _build_msal_app(cache=cache)
    accounts = cca.get_accounts()
    if accounts:  # So all account(s) belong to the current signed-in user
        result = cca.acquire_token_silent(scope, account=accounts[0])
        _save_cache(cache)
        return result
