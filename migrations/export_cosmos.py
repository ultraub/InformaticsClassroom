"""
Export all data from Azure Cosmos DB to JSON files for migration to PostgreSQL.

This script:
1. Connects to Cosmos DB using credentials from .env
2. Lists all containers (collections)
3. Exports each container's documents to a JSON file
4. Stores exports in migrations/cosmos_export/ directory
"""

import os
import json
from pathlib import Path
from azure.cosmos import CosmosClient, exceptions
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Get Cosmos DB credentials
COSMOS_URL = os.getenv('COSMOS_URL')
COSMOS_KEY = os.getenv('COSMOS_KEY')
COSMOS_DATABASE = os.getenv('COSMOS_DATABASE_PROD', 'bids-class')

# Create export directory
EXPORT_DIR = Path(__file__).parent / 'cosmos_export'
EXPORT_DIR.mkdir(exist_ok=True)

def export_cosmos_data():
    """Export all Cosmos DB data to JSON files."""
    print(f"Connecting to Cosmos DB: {COSMOS_URL}")
    print(f"Database: {COSMOS_DATABASE}")

    # Initialize Cosmos client
    client = CosmosClient(COSMOS_URL, COSMOS_KEY)
    database = client.get_database_client(COSMOS_DATABASE)

    # Get all containers
    containers = list(database.list_containers())
    print(f"\nFound {len(containers)} containers to export")

    # Export metadata
    export_metadata = {
        'export_timestamp': datetime.utcnow().isoformat(),
        'source_database': COSMOS_DATABASE,
        'containers': []
    }

    # Export each container
    for container_props in containers:
        container_name = container_props['id']
        print(f"\nExporting container: {container_name}")

        try:
            container = database.get_container_client(container_name)

            # Query all documents
            query = "SELECT * FROM c"
            items = list(container.query_items(
                query=query,
                enable_cross_partition_query=True
            ))

            print(f"  Found {len(items)} documents")

            # Save to JSON file
            output_file = EXPORT_DIR / f"{container_name}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(items, f, indent=2, default=str)

            print(f"  Saved to: {output_file}")

            # Add to metadata
            export_metadata['containers'].append({
                'name': container_name,
                'document_count': len(items),
                'export_file': f"{container_name}.json"
            })

        except exceptions.CosmosHttpResponseError as e:
            print(f"  Error exporting {container_name}: {e}")
            export_metadata['containers'].append({
                'name': container_name,
                'error': str(e)
            })

    # Save export metadata
    metadata_file = EXPORT_DIR / 'export_metadata.json'
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(export_metadata, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Export completed successfully!")
    print(f"Exported {len([c for c in export_metadata['containers'] if 'document_count' in c])} containers")
    print(f"Total documents: {sum(c.get('document_count', 0) for c in export_metadata['containers'])}")
    print(f"Export location: {EXPORT_DIR}")
    print(f"Metadata: {metadata_file}")
    print(f"{'='*60}")

    return export_metadata

if __name__ == '__main__':
    try:
        metadata = export_cosmos_data()

        # Print summary
        print("\nExport Summary:")
        for container in metadata['containers']:
            if 'document_count' in container:
                print(f"  ✓ {container['name']}: {container['document_count']} documents")
            else:
                print(f"  ✗ {container['name']}: {container.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"\nError during export: {e}")
        raise
