"""
Database Adapter Factory

Provides factory functions for creating database adapters based on configuration
"""

import os
from typing import Optional
from informatics_classroom.config import Config
from .interface import DatabaseAdapter
from .cosmos_adapter import CosmosDBAdapter
from .postgres_adapter import PostgreSQLAdapter


def get_database_adapter(
    database_type: Optional[str] = None,
    database_name: Optional[str] = None,
    **kwargs
) -> DatabaseAdapter:
    """
    Factory function to create the appropriate database adapter

    Args:
        database_type: Type of database ('cosmos' or 'postgresql')
                      Defaults to DATABASE_TYPE environment variable or 'cosmos'
        database_name: Database name (defaults to Config.DATABASE)
        **kwargs: Additional adapter-specific configuration

    Returns:
        DatabaseAdapter instance

    Environment Variables (for PostgreSQL):
        DATABASE_TYPE: 'cosmos' or 'postgresql'
        POSTGRES_HOST: PostgreSQL host (default: localhost)
        POSTGRES_PORT: PostgreSQL port (default: 5432)
        POSTGRES_USER: PostgreSQL user
        POSTGRES_PASSWORD: PostgreSQL password
        POSTGRES_DB: PostgreSQL database name

    Usage:
        # Use default (Cosmos DB)
        db = get_database_adapter()

        # Explicitly use PostgreSQL
        db = get_database_adapter(database_type='postgresql')

        # Use with custom configuration
        db = get_database_adapter(
            database_type='postgresql',
            host='mydb.example.com',
            port=5432,
            user='myuser',
            password='mypassword'
        )
    """

    database_type = database_type or os.getenv('DATABASE_TYPE', 'postgresql')
    database_name = database_name or Config.DATABASE

    if database_type == 'cosmos':
        return CosmosDBAdapter(database_name=database_name, **kwargs)

    elif database_type == 'postgresql':
        # Get PostgreSQL configuration from environment or kwargs
        config = {
            'host': kwargs.get('host') or os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(kwargs.get('port') or os.getenv('POSTGRES_PORT', '5432')),
            'user': kwargs.get('user') or os.getenv('POSTGRES_USER'),
            'password': kwargs.get('password') or os.getenv('POSTGRES_PASSWORD'),
        }

        # Validate required PostgreSQL credentials
        if not config['user'] or not config['password']:
            raise ValueError(
                "PostgreSQL requires POSTGRES_USER and POSTGRES_PASSWORD to be set"
            )

        return PostgreSQLAdapter(
            database_name=database_name,
            **config
        )

    else:
        raise ValueError(f"Unsupported database type: {database_type}")


# Singleton instance for the default database
_default_adapter: Optional[DatabaseAdapter] = None


def get_default_adapter() -> DatabaseAdapter:
    """
    Get or create the default database adapter singleton

    This adapter is initialized once and reused throughout the application
    """
    global _default_adapter

    if _default_adapter is None:
        _default_adapter = get_database_adapter()

    return _default_adapter


def reset_default_adapter():
    """
    Reset the default adapter (useful for testing or database switching)
    """
    global _default_adapter

    if _default_adapter:
        _default_adapter.close()
        _default_adapter = None
