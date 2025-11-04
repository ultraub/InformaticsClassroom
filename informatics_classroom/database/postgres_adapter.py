"""
PostgreSQL Database Adapter

Implements the DatabaseAdapter interface for PostgreSQL with JSONB support
"""

import json
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2 import sql
from typing import Dict, List, Optional
from .interface import DatabaseAdapter


class PostgreSQLAdapter(DatabaseAdapter):
    """
    PostgreSQL adapter with JSONB support for document storage

    Schema Design:
    - Each "collection" is a table with columns:
      - id TEXT PRIMARY KEY
      - data JSONB (contains all document fields)
      - created_at TIMESTAMP
      - updated_at TIMESTAMP

    This design allows:
    - Document-style storage (like Cosmos DB)
    - Fast JSON queries with JSONB indexing
    - Easy migration from Cosmos DB
    - PostgreSQL advantages (transactions, joins, constraints)
    """

    def __init__(
        self,
        database_name: str,
        host: str = 'localhost',
        port: int = 5432,
        user: str = None,
        password: str = None,
        **kwargs
    ):
        """
        Initialize PostgreSQL connection

        Args:
            database_name: Database name
            host: Database host
            port: Database port
            user: Database user
            password: Database password
        """
        self.database_name = database_name
        self.host = host
        self.port = port
        self.user = user
        self.password = password

        self.conn = psycopg2.connect(
            dbname=database_name,
            host=host,
            port=port,
            user=user,
            password=password,
            cursor_factory=RealDictCursor
        )
        self.conn.autocommit = True
        self._in_transaction = False

    def _get_cursor(self):
        """Get a database cursor"""
        return self.conn.cursor()

    def _ensure_collection_exists(self, collection: str):
        """Ensure the collection table exists, create if not"""
        if not self.collection_exists(collection):
            self.create_collection(collection)

    # ========== Document Operations ==========

    def get(self, collection: str, id: str) -> Optional[Dict]:
        """Retrieve a document by ID"""
        self._ensure_collection_exists(collection)

        with self._get_cursor() as cur:
            query = sql.SQL("""
                SELECT data FROM {} WHERE id = %s
            """).format(sql.Identifier(collection))

            cur.execute(query, (id,))
            result = cur.fetchone()

            if result:
                document = dict(result['data'])
                document['id'] = id
                return document

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
        self._ensure_collection_exists(collection)

        # Build WHERE clause from filters
        where_conditions = []
        params = []

        if filters:
            for key, value in filters.items():
                # Use JSONB containment operator
                where_conditions.append("data @> %s")
                params.append(Json({key: value}))

        where_clause = " AND ".join(where_conditions) if where_conditions else "TRUE"

        # Build field selection
        if fields:
            field_selects = []
            for field in fields:
                field_selects.append(f"data->'{field}' as {field}")
            select_clause = "id, " + ", ".join(field_selects)
        else:
            select_clause = "id, data"

        # Build ORDER BY clause
        order_clause = ""
        if order_by:
            order_clause = f"ORDER BY data->>'{order_by}'"

        # Build LIMIT/OFFSET
        limit_clause = f"LIMIT {limit}" if limit else ""
        offset_clause = f"OFFSET {offset}" if offset else ""

        with self._get_cursor() as cur:
            query = f"""
                SELECT {select_clause}
                FROM {collection}
                WHERE {where_clause}
                {order_clause}
                {limit_clause}
                {offset_clause}
            """

            cur.execute(query, params)
            results = cur.fetchall()

            documents = []
            for row in results:
                if fields:
                    doc = {'id': row['id']}
                    for field in fields:
                        doc[field] = row.get(field)
                else:
                    doc = dict(row['data'])
                    doc['id'] = row['id']
                documents.append(doc)

            return documents

    def query_raw(
        self,
        collection: str,
        query: str,
        parameters: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """Execute a raw SQL query"""
        self._ensure_collection_exists(collection)

        # Convert Cosmos-style parameters to PostgreSQL format
        sql_query = query
        params = []

        if parameters:
            for param in parameters:
                param_name = param['name']
                param_value = param['value']
                # Replace @param_name with %s
                sql_query = sql_query.replace(param_name, '%s')
                params.append(param_value)

        with self._get_cursor() as cur:
            cur.execute(sql_query, params)
            results = cur.fetchall()

            documents = []
            for row in results:
                doc = dict(row)
                documents.append(doc)

            return documents

    def insert(self, collection: str, document: Dict) -> Dict:
        """Insert a new document"""
        self._ensure_collection_exists(collection)

        doc_id = document.get('id')
        if not doc_id:
            raise ValueError("Document must have an 'id' field")

        # Remove id from data to avoid duplication
        data = {k: v for k, v in document.items() if k != 'id'}

        with self._get_cursor() as cur:
            query = sql.SQL("""
                INSERT INTO {} (id, data, created_at, updated_at)
                VALUES (%s, %s, NOW(), NOW())
                RETURNING id, data
            """).format(sql.Identifier(collection))

            cur.execute(query, (doc_id, Json(data)))
            result = cur.fetchone()

            inserted_doc = dict(result['data'])
            inserted_doc['id'] = result['id']
            return inserted_doc

    def update(self, collection: str, id: str, updates: Dict) -> Dict:
        """Update an existing document"""
        self._ensure_collection_exists(collection)

        # Use JSONB merge operation
        with self._get_cursor() as cur:
            query = sql.SQL("""
                UPDATE {}
                SET data = data || %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id, data
            """).format(sql.Identifier(collection))

            cur.execute(query, (Json(updates), id))
            result = cur.fetchone()

            if not result:
                raise ValueError(f"Document with id '{id}' not found")

            updated_doc = dict(result['data'])
            updated_doc['id'] = result['id']
            return updated_doc

    def upsert(self, collection: str, document: Dict) -> Dict:
        """Insert or update a document"""
        self._ensure_collection_exists(collection)

        doc_id = document.get('id')
        if not doc_id:
            raise ValueError("Document must have an 'id' field")

        # Remove id from data
        data = {k: v for k, v in document.items() if k != 'id'}

        with self._get_cursor() as cur:
            query = sql.SQL("""
                INSERT INTO {} (id, data, created_at, updated_at)
                VALUES (%s, %s, NOW(), NOW())
                ON CONFLICT (id)
                DO UPDATE SET data = EXCLUDED.data, updated_at = NOW()
                RETURNING id, data
            """).format(sql.Identifier(collection))

            cur.execute(query, (doc_id, Json(data)))
            result = cur.fetchone()

            upserted_doc = dict(result['data'])
            upserted_doc['id'] = result['id']
            return upserted_doc

    def delete(self, collection: str, id: str) -> bool:
        """Delete a document"""
        self._ensure_collection_exists(collection)

        with self._get_cursor() as cur:
            query = sql.SQL("""
                DELETE FROM {} WHERE id = %s
            """).format(sql.Identifier(collection))

            cur.execute(query, (id,))
            return cur.rowcount > 0

    # ========== Batch Operations ==========

    def bulk_insert(self, collection: str, documents: List[Dict]) -> int:
        """Insert multiple documents"""
        self._ensure_collection_exists(collection)

        count = 0
        with self._get_cursor() as cur:
            query = sql.SQL("""
                INSERT INTO {} (id, data, created_at, updated_at)
                VALUES (%s, %s, NOW(), NOW())
            """).format(sql.Identifier(collection))

            for doc in documents:
                doc_id = doc.get('id')
                if not doc_id:
                    continue

                data = {k: v for k, v in doc.items() if k != 'id'}
                cur.execute(query, (doc_id, Json(data)))
                count += cur.rowcount

        return count

    def bulk_update(self, collection: str, updates: List[Dict]) -> int:
        """Update multiple documents"""
        self._ensure_collection_exists(collection)

        count = 0
        for update_op in updates:
            doc_id = update_op.get('id')
            update_data = update_op.get('updates', {})

            if doc_id and update_data:
                self.update(collection, doc_id, update_data)
                count += 1

        return count

    def bulk_delete(self, collection: str, ids: List[str]) -> int:
        """Delete multiple documents"""
        self._ensure_collection_exists(collection)

        if not ids:
            return 0

        with self._get_cursor() as cur:
            query = sql.SQL("""
                DELETE FROM {} WHERE id = ANY(%s)
            """).format(sql.Identifier(collection))

            cur.execute(query, (ids,))
            return cur.rowcount

    # ========== Collection Management ==========

    def collection_exists(self, collection: str) -> bool:
        """Check if a collection exists"""
        with self._get_cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = %s
                )
            """, (collection,))
            return cur.fetchone()['exists']

    def create_collection(self, collection: str, **options) -> bool:
        """Create a new collection table"""
        if self.collection_exists(collection):
            return False

        with self._get_cursor() as cur:
            # Create table
            query = sql.SQL("""
                CREATE TABLE {} (
                    id TEXT PRIMARY KEY,
                    data JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """).format(sql.Identifier(collection))
            cur.execute(query)

            # Create GIN index on JSONB data for fast queries
            index_query = sql.SQL("""
                CREATE INDEX {}_data_idx ON {} USING GIN (data)
            """).format(
                sql.Identifier(f"{collection}_data"),
                sql.Identifier(collection)
            )
            cur.execute(index_query)

        return True

    def drop_collection(self, collection: str) -> bool:
        """Drop a collection table"""
        if not self.collection_exists(collection):
            return False

        with self._get_cursor() as cur:
            query = sql.SQL("DROP TABLE {}").format(sql.Identifier(collection))
            cur.execute(query)

        return True

    def count(self, collection: str, filters: Optional[Dict] = None) -> int:
        """Count documents in collection"""
        if not self.collection_exists(collection):
            return 0

        where_conditions = []
        params = []

        if filters:
            for key, value in filters.items():
                where_conditions.append("data @> %s")
                params.append(Json({key: value}))

        where_clause = " AND ".join(where_conditions) if where_conditions else "TRUE"

        with self._get_cursor() as cur:
            query = f"SELECT COUNT(*) FROM {collection} WHERE {where_clause}"
            cur.execute(query, params)
            return cur.fetchone()['count']

    # ========== Transaction Support ==========

    def begin_transaction(self):
        """Begin a transaction"""
        self.conn.autocommit = False
        self._in_transaction = True

    def commit_transaction(self):
        """Commit the transaction"""
        self.conn.commit()
        self.conn.autocommit = True
        self._in_transaction = False

    def rollback_transaction(self):
        """Rollback the transaction"""
        self.conn.rollback()
        self.conn.autocommit = True
        self._in_transaction = False

    # ========== Connection Management ==========

    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()

    def ping(self) -> bool:
        """Test database connection"""
        try:
            with self._get_cursor() as cur:
                cur.execute("SELECT 1")
                return True
        except Exception:
            return False

    # ========== Database Info ==========

    def get_database_type(self) -> str:
        """Get database type identifier"""
        return 'postgresql'

    def get_collections(self) -> List[str]:
        """Get list of all tables"""
        with self._get_cursor() as cur:
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
            """)
            return [row['table_name'] for row in cur.fetchall()]
