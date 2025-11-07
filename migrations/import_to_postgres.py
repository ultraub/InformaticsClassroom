"""
Import data from Cosmos DB export files into PostgreSQL.

This script:
1. Reads JSON export files from migrations/cosmos_export/
2. Creates tables in PostgreSQL using the DatabaseAdapter schema
3. Imports all documents into PostgreSQL
4. Validates the import
"""

import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to import database adapter
sys.path.insert(0, str(Path(__file__).parent.parent))

from informatics_classroom.database.postgres_adapter import PostgreSQLAdapter

# Load environment variables
load_dotenv()

# PostgreSQL configuration
POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),
    'user': os.getenv('POSTGRES_USER', 'informatics_admin'),
    'password': os.getenv('POSTGRES_PASSWORD', 'informatics_local_dev'),
    'database_name': os.getenv('POSTGRES_DB', 'informatics_classroom')
}

# Export directory
EXPORT_DIR = Path(__file__).parent / 'cosmos_export'

def import_collection(adapter: PostgreSQLAdapter, collection_name: str, documents: list) -> tuple:
    """Import a collection into PostgreSQL."""
    print(f"\nImporting collection: {collection_name}")
    print(f"  Documents to import: {len(documents)}")

    # Create the collection (table)
    try:
        adapter.create_collection(collection_name)
        print(f"  ✓ Created table: {collection_name}")
    except Exception as e:
        # Table might already exist
        print(f"  Table {collection_name} may already exist: {e}")

    # Import documents
    success_count = 0
    error_count = 0

    for i, doc in enumerate(documents):
        try:
            # Use upsert to handle both new and existing documents
            adapter.upsert(collection_name, doc)
            success_count += 1

            # Progress indicator
            if (i + 1) % 1000 == 0:
                print(f"  Progress: {i + 1}/{len(documents)} documents imported...")

        except Exception as e:
            error_count += 1
            if error_count <= 5:  # Only print first 5 errors
                print(f"  Error importing document {doc.get('id', 'unknown')}: {e}")

    print(f"  ✓ Import complete: {success_count} success, {error_count} errors")
    return success_count, error_count

def validate_import(adapter: PostgreSQLAdapter, collection_name: str, expected_count: int) -> bool:
    """Validate that all documents were imported correctly."""
    try:
        # Query all documents
        documents = adapter.query(collection_name)
        actual_count = len(documents)

        if actual_count == expected_count:
            print(f"  ✓ Validation passed: {actual_count} documents")
            return True
        else:
            print(f"  ✗ Validation failed: expected {expected_count}, found {actual_count}")
            return False

    except Exception as e:
        print(f"  ✗ Validation error: {e}")
        return False

def main():
    """Main import process."""
    print("="*60)
    print("PostgreSQL Data Import")
    print("="*60)

    # Check if export directory exists
    if not EXPORT_DIR.exists():
        print(f"\nError: Export directory not found: {EXPORT_DIR}")
        print("Please run export_cosmos.py first to export data from Cosmos DB")
        return False

    # Load export metadata
    metadata_file = EXPORT_DIR / 'export_metadata.json'
    if not metadata_file.exists():
        print(f"\nError: Export metadata not found: {metadata_file}")
        return False

    with open(metadata_file, 'r') as f:
        metadata = json.load(f)

    print(f"\nExport info:")
    print(f"  Source: {metadata.get('source_database')}")
    print(f"  Timestamp: {metadata.get('export_timestamp')}")
    print(f"  Containers: {len(metadata.get('containers', []))}")

    # Initialize PostgreSQL adapter
    print(f"\nConnecting to PostgreSQL:")
    print(f"  Host: {POSTGRES_CONFIG['host']}")
    print(f"  Port: {POSTGRES_CONFIG['port']}")
    print(f"  Database: {POSTGRES_CONFIG['database_name']}")

    # Try to connect, if database doesn't exist create it
    try:
        adapter = PostgreSQLAdapter(**POSTGRES_CONFIG)
        print("  ✓ Connected successfully")
    except Exception as e:
        if "does not exist" in str(e):
            print(f"  Database doesn't exist, attempting to create it...")
            # Connect to postgres database to create our database
            import psycopg2
            conn = psycopg2.connect(
                dbname='postgres',
                host=POSTGRES_CONFIG['host'],
                port=POSTGRES_CONFIG['port'],
                user=POSTGRES_CONFIG['user'],
                password=POSTGRES_CONFIG['password']
            )
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute(f"CREATE DATABASE {POSTGRES_CONFIG['database_name']}")
            cur.close()
            conn.close()
            print(f"  ✓ Created database: {POSTGRES_CONFIG['database_name']}")

            # Now connect to the new database
            adapter = PostgreSQLAdapter(**POSTGRES_CONFIG)
            print("  ✓ Connected successfully")
        else:
            raise

    # Import each collection
    total_imported = 0
    total_errors = 0
    import_summary = []

    for container_info in metadata['containers']:
        if 'error' in container_info:
            print(f"\nSkipping {container_info['name']} (export error)")
            continue

        collection_name = container_info['name']
        export_file = EXPORT_DIR / container_info['export_file']

        # Load exported data
        with open(export_file, 'r', encoding='utf-8') as f:
            documents = json.load(f)

        # Import collection
        success, errors = import_collection(adapter, collection_name, documents)
        total_imported += success
        total_errors += errors

        # Validate import
        validation_passed = validate_import(adapter, collection_name, len(documents))

        import_summary.append({
            'collection': collection_name,
            'expected': len(documents),
            'imported': success,
            'errors': errors,
            'validated': validation_passed
        })

    # Print summary
    print(f"\n{'='*60}")
    print("Import Summary")
    print(f"{'='*60}")

    for summary in import_summary:
        status = "✓" if summary['validated'] else "✗"
        print(f"{status} {summary['collection']}:")
        print(f"    Expected: {summary['expected']}")
        print(f"    Imported: {summary['imported']}")
        if summary['errors'] > 0:
            print(f"    Errors: {summary['errors']}")

    print(f"\nTotal documents imported: {total_imported}")
    if total_errors > 0:
        print(f"Total errors: {total_errors}")

    all_validated = all(s['validated'] for s in import_summary)
    if all_validated:
        print(f"\n{'='*60}")
        print("✓ All collections imported and validated successfully!")
        print(f"{'='*60}")
        return True
    else:
        print(f"\n{'='*60}")
        print("✗ Some collections failed validation")
        print(f"{'='*60}")
        return False

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Import failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
