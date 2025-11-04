"""
Database Abstraction Layer

Provides a unified interface for database operations that works with:
- Azure Cosmos DB (current)
- PostgreSQL with JSONB (future migration target)

This abstraction allows the application to be database-agnostic and
facilitates migration from Cosmos DB to PostgreSQL.
"""

from .interface import DatabaseAdapter
from .factory import get_database_adapter
from .cosmos_adapter import CosmosDBAdapter
from .postgres_adapter import PostgreSQLAdapter

__all__ = [
    'DatabaseAdapter',
    'get_database_adapter',
    'CosmosDBAdapter',
    'PostgreSQLAdapter'
]
