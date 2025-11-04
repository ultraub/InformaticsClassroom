# InformaticsClassroom Setup Guide

## Prerequisites

- Python 3.8 or higher
- Azure subscription with the following services configured:
  - Azure AD (for authentication)
  - Azure Cosmos DB (for data storage)
  - Azure Table Storage
  - Azure Blob Storage
- pip (Python package manager)

## Environment Configuration

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd InformaticsClassroom
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: If `python-dotenv` is not in requirements.txt, install it:
```bash
pip install python-dotenv
```

### Step 4: Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your Azure credentials:

```bash
# Flask Configuration
FLASK_SECRET_KEY=<generate-a-strong-random-key>
FLASK_DEBUG=False
FLASK_TESTING=False

# Azure AD / MSAL Configuration
AZURE_CLIENT_ID=<your-app-registration-client-id>
AZURE_CLIENT_SECRET=<your-app-registration-client-secret>
AZURE_AUTHORITY=https://login.microsoftonline.com/common
AZURE_REDIRECT_PATH=/getAToken
AZURE_AUTH_DOMAIN=jh

# Azure Cosmos DB Configuration
COSMOS_URL=<your-cosmos-db-url>
COSMOS_KEY=<your-cosmos-db-primary-key>
COSMOS_DATABASE_PROD=bids-class
COSMOS_DATABASE_DEV=bids-class-dev

# Azure Table Storage Configuration
AZURE_STORAGE_ACCOUNT_NAME=<your-storage-account-name>
AZURE_STORAGE_KEY=<your-storage-account-key>

# Azure Blob Storage Configuration
AZURE_BLOB_CONTAINER_NAME=figures
AZURE_BLOB_CONNECT_STR=<your-blob-storage-connection-string>

# Microsoft Graph API Configuration
AZURE_GRAPH_ENDPOINT=https://graph.microsoft.com/v1.0/users
AZURE_GRAPH_SCOPE=User.ReadBasic.All
```

### Step 5: Obtain Azure Credentials

#### Azure AD App Registration

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **New registration**
4. Configure:
   - **Name**: InformaticsClassroom
   - **Supported account types**: Accounts in any organizational directory (Multitenant)
   - **Redirect URI**: Web → `http://localhost:5000/getAToken` (for local development)
5. After creation, note the **Application (client) ID** → use for `AZURE_CLIENT_ID`
6. Go to **Certificates & secrets** → **New client secret**
7. Copy the secret value → use for `AZURE_CLIENT_SECRET`

#### Azure Cosmos DB

1. Navigate to your Cosmos DB account
2. Go to **Settings** → **Keys**
3. Copy the **URI** → use for `COSMOS_URL`
4. Copy the **PRIMARY KEY** → use for `COSMOS_KEY`

#### Azure Storage Account

1. Navigate to your Storage Account
2. Go to **Settings** → **Access keys**
3. Copy **Storage account name** → use for `AZURE_STORAGE_ACCOUNT_NAME`
4. Copy **Key** from key1 or key2 → use for `AZURE_STORAGE_KEY`

#### Azure Blob Storage

1. In the same Storage Account, go to **Settings** → **Access keys**
2. Click **Show** next to **Connection string**
3. Copy the entire connection string → use for `AZURE_BLOB_CONNECT_STR`

### Step 6: Generate Flask Secret Key

Generate a strong secret key for Flask:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Use the output for `FLASK_SECRET_KEY` in your `.env` file.

## Running the Application

### Development Mode

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Set testing mode if needed
export FLASK_TESTING=True  # On Windows: set FLASK_TESTING=True

# Run the application
python run.py
```

The application will be available at `http://localhost:5000`

### Production Mode

For production deployment:

1. Set `FLASK_DEBUG=False` in `.env`
2. Set `FLASK_TESTING=False` in `.env`
3. Use a production WSGI server like Gunicorn:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:8000 "informatics_classroom:create_app()"
   ```

## Security Best Practices

### ⚠️ IMPORTANT: Never commit secrets to version control

- The `.env` file is excluded in `.gitignore`
- Never commit `.env` to Git
- Never share `.env` files via email or messaging
- Use Azure Key Vault for production secrets

### For Production Deployments

Consider using Azure Key Vault instead of environment variables:

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://<your-key-vault>.vault.azure.net/", credential=credential)

SECRET_KEY = client.get_secret("flask-secret-key").value
CLIENT_SECRET = client.get_secret("azure-client-secret").value
```

## Troubleshooting

### Missing Environment Variables

If you see errors like `ValueError: FLASK_SECRET_KEY environment variable must be set`:

1. Ensure `.env` file exists in the project root
2. Verify all required variables are set in `.env`
3. Check that `python-dotenv` is installed: `pip install python-dotenv`

### Azure Authentication Failures

- Verify `AZURE_CLIENT_ID` and `AZURE_CLIENT_SECRET` are correct
- Check that redirect URI in Azure AD matches your application URL
- Ensure the app registration has the correct API permissions

### Database Connection Errors

- Verify `COSMOS_URL` and `COSMOS_KEY` are correct
- Check that your IP address is allowed in Cosmos DB firewall rules
- Ensure the database name matches in both `.env` and Azure

## Testing

To run in testing mode:

```bash
export FLASK_TESTING=True
python run.py
```

This will:
- Use the development database (`COSMOS_DATABASE_DEV`)
- Enable mock authentication (bypasses Azure AD)
- Use test user: `rbarre16@jh.edu`

## Additional Resources

- [Azure AD Authentication](https://docs.microsoft.com/en-us/azure/active-directory/develop/)
- [Azure Cosmos DB Documentation](https://docs.microsoft.com/en-us/azure/cosmos-db/)
- [Flask Configuration](https://flask.palletsprojects.com/en/latest/config/)
- [python-dotenv Documentation](https://github.com/theskumar/python-dotenv)
