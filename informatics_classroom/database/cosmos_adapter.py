"""
Azure Cosmos DB Adapter

Implements the DatabaseAdapter interface for Azure Cosmos DB (current system)
Wraps the existing azure_func.init_cosmos functionality

DEPRECATED: This adapter is maintained for backward compatibility only.
PostgreSQL is now the primary database.
"""

import warnings
from typing import Dict, List, Optional
from informatics_classroom.azure_func import init_cosmos
from .interface import DatabaseAdapter


class CosmosDBAdapter(DatabaseAdapter):
    """
    Azure Cosmos DB adapter

    Wraps existing Cosmos DB functionality to provide the unified
    DatabaseAdapter interface
    """

    def __init__(self, database_name: str, **kwargs):
        """
        Initialize Cosmos DB adapter

        Args:
            database_name: Cosmos database name
        """
        warnings.warn(
            "CosmosDBAdapter is deprecated. PostgreSQL is now the primary database. "
            "This adapter is maintained for backward compatibility only.",
            DeprecationWarning,
            stacklevel=2
        )
        self.database_name = database_name
        self._containers = {}  # Cache of container clients

    def _get_container(self, collection: str):
        """Get or create container client for a collection"""
        if collection not in self._containers:
            self._containers[collection] = init_cosmos(collection, self.database_name)
        return self._containers[collection]

    # ========== Document Operations ==========

    def get(self, collection: str, id: str) -> Optional[Dict]:
        """Retrieve a document by ID"""
        try:
            container = self._get_container(collection)
            return container.read_item(item=id, partition_key=id)
        except Exception:
            return None

    def query(
        self,
        collection: str,
        filters: Optional[Dict] = None,
        fields: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None
    ) -> List[Dict]:
        """Query documents with filters"""
        # Build Cosmos DB SQL query
        select_clause = "*"
        if fields:
            select_clause = ", ".join(f"c.{field}" for field in fields)

        where_conditions = []
        parameters = []

        if filters:
            for i, (key, value) in enumerate(filters.items()):
                param_name = f"@param{i}"
                where_conditions.append(f"c.{key} = {param_name}")
                parameters.append({"name": param_name, "value": value})

        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""

        order_clause = f"ORDER BY c.{order_by}" if order_by else ""

        offset_clause = f"OFFSET {offset}" if offset else ""
        limit_clause = f"LIMIT {limit}" if limit else ""

        query = f"""
            SELECT {select_clause} FROM c
            {where_clause}
            {order_clause}
            {offset_clause}
            {limit_clause}
        """

        return self.query_raw(collection, query, parameters)

    def query_raw(
        self,
        collection: str,
        query: str,
        parameters: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """Execute a raw Cosmos DB SQL query"""
        container = self._get_container(collection)

        results = container.query_items(
            query=query,
            parameters=parameters or [],
            enable_cross_partition_query=True
        )

        return list(results)

    def insert(self, collection: str, document: Dict) -> Dict:
        """Insert a new document"""
        container = self._get_container(collection)
        return container.create_item(body=document)

    def update(self, collection: str, id: str, updates: Dict) -> Dict:
        """Update an existing document"""
        # Cosmos DB doesn't have partial update, need to read-modify-write
        doc = self.get(collection, id)
        if not doc:
            raise ValueError(f"Document with id '{id}' not found")

        doc.update(updates)
        return self.upsert(collection, doc)

    def upsert(self, collection: str, document: Dict) -> Dict:
        """Insert or update a document"""
        container = self._get_container(collection)
        return container.upsert_item(body=document)

    def delete(self, collection: str, id: str) -> bool:
        """Delete a document"""
        try:
            container = self._get_container(collection)
            container.delete_item(item=id, partition_key=id)
            return True
        except Exception:
            return False

    # ========== Batch Operations ==========

    def bulk_insert(self, collection: str, documents: List[Dict]) -> int:
        """Insert multiple documents"""
        container = self._get_container(collection)
        count = 0

        for doc in documents:
            try:
                container.create_item(body=doc)
                count += 1
            except Exception:
                continue

        return count

    def bulk_update(self, collection: str, updates: List[Dict]) -> int:
        """Update multiple documents"""
        count = 0

        for update_op in updates:
            doc_id = update_op.get('id')
            update_data = update_op.get('updates', {})

            if doc_id and update_data:
                try:
                    self.update(collection, doc_id, update_data)
                    count += 1
                except Exception:
                    continue

        return count

    def bulk_delete(self, collection: str, ids: List[str]) -> int:
        """Delete multiple documents"""
        container = self._get_container(collection)
        count = 0

        for doc_id in ids:
            try:
                container.delete_item(item=doc_id, partition_key=doc_id)
                count += 1
            except Exception:
                continue

        return count

    # ========== Collection Management ==========

    def collection_exists(self, collection: str) -> bool:
        """Check if a container exists"""
        try:
            self._get_container(collection)
            return True
        except Exception:
            return False

    def create_collection(self, collection: str, **options) -> bool:
        """
        Create a new container

        Note: Cosmos DB requires partition key specification
        Options should include: partition_key_path
        """
        # This would require access to database client, not just container
        # For now, assume containers are pre-created
        raise NotImplementedError("Container creation not supported via this adapter")

    def drop_collection(self, collection: str) -> bool:
        """Drop a container"""
        # This would require access to database client
        raise NotImplementedError("Container deletion not supported via this adapter")

    def count(self, collection: str, filters: Optional[Dict] = None) -> int:
        """Count documents in collection"""
        where_conditions = []
        parameters = []

        if filters:
            for i, (key, value) in enumerate(filters.items()):
                param_name = f"@param{i}"
                where_conditions.append(f"c.{key} = {param_name}")
                parameters.append({"name": param_name, "value": value})

        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""

        query = f"SELECT VALUE COUNT(1) FROM c {where_clause}"

        results = self.query_raw(collection, query, parameters)
        return results[0] if results else 0

    # ========== Transaction Support ==========

    def begin_transaction(self):
        """Begin a transaction (not supported in Cosmos DB)"""
        # Cosmos DB uses automatic transactions at document level
        pass

    def commit_transaction(self):
        """Commit transaction (not supported in Cosmos DB)"""
        pass

    def rollback_transaction(self):
        """Rollback transaction (not supported in Cosmos DB)"""
        pass

    # ========== Connection Management ==========

    def close(self):
        """Close connections"""
        self._containers.clear()

    def ping(self) -> bool:
        """Test database connection"""
        try:
            # Try to access users container as a health check
            container = self._get_container('users')
            container.read_all_items(max_item_count=1)
            return True
        except Exception:
            return False

    # ========== Database Info ==========

    def get_database_type(self) -> str:
        """Get database type identifier"""
        return 'cosmos'

    def get_collections(self) -> List[str]:
        """Get list of all containers"""
        # Would require database client access
        # Return known collections for now
        return ['users', 'quiz', 'answer', 'tokens', 'classes']
