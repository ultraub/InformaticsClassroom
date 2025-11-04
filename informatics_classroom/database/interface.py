"""
Database Adapter Interface

Defines the abstract interface that all database adapters must implement
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class DatabaseAdapter(ABC):
    """
    Abstract base class for database adapters

    All database implementations (Cosmos DB, PostgreSQL, etc.) must
    implement these methods to provide a unified interface.
    """

    @abstractmethod
    def __init__(self, database_name: str, **kwargs):
        """
        Initialize the database adapter

        Args:
            database_name: Name of the database to connect to
            **kwargs: Additional configuration specific to the adapter
        """
        pass

    # ========== Document/Row Operations ==========

    @abstractmethod
    def get(self, collection: str, id: str) -> Optional[Dict]:
        """
        Retrieve a single document/row by ID

        Args:
            collection: Collection/table name
            id: Document/row ID

        Returns:
            Document as dictionary or None if not found
        """
        pass

    @abstractmethod
    def query(
        self,
        collection: str,
        filters: Optional[Dict] = None,
        fields: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None
    ) -> List[Dict]:
        """
        Query documents/rows with filters

        Args:
            collection: Collection/table name
            filters: Dictionary of field: value filters
            fields: List of fields to return (None = all fields)
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Field to order by

        Returns:
            List of documents as dictionaries
        """
        pass

    @abstractmethod
    def query_raw(
        self,
        collection: str,
        query: str,
        parameters: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Execute a raw query in the native database language

        Args:
            collection: Collection/table name
            query: Raw query string (SQL for PostgreSQL, Cosmos SQL for Cosmos)
            parameters: Query parameters

        Returns:
            List of documents as dictionaries
        """
        pass

    @abstractmethod
    def insert(self, collection: str, document: Dict) -> Dict:
        """
        Insert a new document/row

        Args:
            collection: Collection/table name
            document: Document to insert

        Returns:
            Inserted document with any auto-generated fields
        """
        pass

    @abstractmethod
    def update(self, collection: str, id: str, updates: Dict) -> Dict:
        """
        Update an existing document/row

        Args:
            collection: Collection/table name
            id: Document/row ID
            updates: Dictionary of fields to update

        Returns:
            Updated document
        """
        pass

    @abstractmethod
    def upsert(self, collection: str, document: Dict) -> Dict:
        """
        Insert or update a document/row

        Args:
            collection: Collection/table name
            document: Document to upsert (must include 'id' field)

        Returns:
            Upserted document
        """
        pass

    @abstractmethod
    def delete(self, collection: str, id: str) -> bool:
        """
        Delete a document/row

        Args:
            collection: Collection/table name
            id: Document/row ID

        Returns:
            True if deleted, False if not found
        """
        pass

    # ========== Batch Operations ==========

    @abstractmethod
    def bulk_insert(self, collection: str, documents: List[Dict]) -> int:
        """
        Insert multiple documents/rows

        Args:
            collection: Collection/table name
            documents: List of documents to insert

        Returns:
            Number of documents inserted
        """
        pass

    @abstractmethod
    def bulk_update(self, collection: str, updates: List[Dict]) -> int:
        """
        Update multiple documents/rows

        Args:
            collection: Collection/table name
            updates: List of update operations [{'id': ..., 'updates': {...}}]

        Returns:
            Number of documents updated
        """
        pass

    @abstractmethod
    def bulk_delete(self, collection: str, ids: List[str]) -> int:
        """
        Delete multiple documents/rows

        Args:
            collection: Collection/table name
            ids: List of document/row IDs

        Returns:
            Number of documents deleted
        """
        pass

    # ========== Collection/Table Management ==========

    @abstractmethod
    def collection_exists(self, collection: str) -> bool:
        """
        Check if a collection/table exists

        Args:
            collection: Collection/table name

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    def create_collection(self, collection: str, **options) -> bool:
        """
        Create a new collection/table

        Args:
            collection: Collection/table name
            **options: Database-specific options

        Returns:
            True if created, False if already exists
        """
        pass

    @abstractmethod
    def drop_collection(self, collection: str) -> bool:
        """
        Drop a collection/table

        Args:
            collection: Collection/table name

        Returns:
            True if dropped, False if didn't exist
        """
        pass

    @abstractmethod
    def count(self, collection: str, filters: Optional[Dict] = None) -> int:
        """
        Count documents/rows in a collection

        Args:
            collection: Collection/table name
            filters: Optional filters to apply

        Returns:
            Count of documents
        """
        pass

    # ========== Transaction Support ==========

    @abstractmethod
    def begin_transaction(self):
        """Begin a database transaction (if supported)"""
        pass

    @abstractmethod
    def commit_transaction(self):
        """Commit the current transaction"""
        pass

    @abstractmethod
    def rollback_transaction(self):
        """Rollback the current transaction"""
        pass

    # ========== Connection Management ==========

    @abstractmethod
    def close(self):
        """Close the database connection"""
        pass

    @abstractmethod
    def ping(self) -> bool:
        """
        Test the database connection

        Returns:
            True if connection is alive, False otherwise
        """
        pass

    # ========== Database Info ==========

    @abstractmethod
    def get_database_type(self) -> str:
        """
        Get the type of database

        Returns:
            String identifier ('cosmos', 'postgresql', etc.)
        """
        pass

    @abstractmethod
    def get_collections(self) -> List[str]:
        """
        Get list of all collections/tables in the database

        Returns:
            List of collection/table names
        """
        pass
