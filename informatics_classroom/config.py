import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    TESTING = os.getenv('FLASK_TESTING', 'False').lower() == 'true'

    # SECURITY: Secrets now loaded from environment variables
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("FLASK_SECRET_KEY environment variable must be set")

    CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
    if not CLIENT_ID:
        raise ValueError("AZURE_CLIENT_ID environment variable must be set")

    CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET')
    if not CLIENT_SECRET:
        raise ValueError("AZURE_CLIENT_SECRET environment variable must be set")

    AUTHORITY = os.getenv('AZURE_AUTHORITY', 'https://login.microsoftonline.com/common')
    REDIRECT_PATH = os.getenv('AZURE_REDIRECT_PATH', '/getAToken')

    # Microsoft Graph API configuration
    ENDPOINT = os.getenv('AZURE_GRAPH_ENDPOINT', 'https://graph.microsoft.com/v1.0/users')
    SCOPE = [os.getenv('AZURE_GRAPH_SCOPE', 'User.ReadBasic.All')]

    SESSION_TYPE = "filesystem"

    # Database selection based on testing mode
    if TESTING:
        DATABASE = os.getenv('COSMOS_DATABASE_DEV', 'bids-class-dev')
    else:
        DATABASE = os.getenv('COSMOS_DATABASE_PROD', 'bids-class')

    # ========== REACT SPA MIGRATION CONFIGURATION ==========

    # Feature flag: Enable React UI (vs Flask templates)
    USE_REACT_UI = os.getenv('USE_REACT_UI', 'true').lower() == 'true'

    # React build path
    REACT_BUILD_PATH = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'informatics-classroom-ui',
        'dist'
    )

    # Role-based rollout configuration
    # Options: 'admins', 'instructors', 'all'
    REACT_ROLLOUT_MODE = os.getenv('REACT_ROLLOUT_MODE', 'admins')

    # Map rollout modes to allowed roles
    REACT_ENABLED_ROLES = {
        'admins': ['admin'],
        'instructors': ['admin', 'instructor'],
        'all': ['admin', 'instructor', 'ta', 'student']
    }.get(REACT_ROLLOUT_MODE, ['admin'])

    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)  # Use Flask secret if not set
    JWT_ALGORITHM = 'HS256'
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '3600'))  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', '2592000'))  # 30 days

class Keys:
    # SECURITY: Azure credentials now loaded from environment variables

    # Azure Table Storage Service
    account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
    if not account_name:
        raise ValueError("AZURE_STORAGE_ACCOUNT_NAME environment variable must be set")

    storage_key = os.getenv('AZURE_STORAGE_KEY')
    if not storage_key:
        raise ValueError("AZURE_STORAGE_KEY environment variable must be set")

    # Azure CosmosDB Access
    url = os.getenv('COSMOS_URL')
    if not url:
        raise ValueError("COSMOS_URL environment variable must be set")

    cosmos_key = os.getenv('COSMOS_KEY')
    if not cosmos_key:
        raise ValueError("COSMOS_KEY environment variable must be set")

    # Azure Blob Storage Service
    blob_container_name = os.getenv('AZURE_BLOB_CONTAINER_NAME', 'figures')
    blob_connect_str = os.getenv('AZURE_BLOB_CONNECT_STR')
    if not blob_connect_str:
        raise ValueError("AZURE_BLOB_CONNECT_STR environment variable must be set")

    # Authentication domain
    auth_domain = os.getenv('AZURE_AUTH_DOMAIN', 'jh')