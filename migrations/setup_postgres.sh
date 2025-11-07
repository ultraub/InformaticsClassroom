#!/bin/bash

# Setup local PostgreSQL database for Informatics Classroom
# This script uses Docker to run PostgreSQL locally

set -e

echo "=========================================="
echo "Setting up PostgreSQL for local development"
echo "=========================================="

# Configuration
POSTGRES_USER="informatics_admin"
POSTGRES_PASSWORD="informatics_local_dev"
POSTGRES_DB="informatics_classroom"
POSTGRES_PORT="5432"
CONTAINER_NAME="informatics-postgres"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    echo "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "Error: Docker is not running"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

echo "✓ Docker is installed and running"

# Stop and remove existing container if it exists
if docker ps -a | grep -q $CONTAINER_NAME; then
    echo "Stopping and removing existing PostgreSQL container..."
    docker stop $CONTAINER_NAME || true
    docker rm $CONTAINER_NAME || true
fi

# Create Docker volume for data persistence
echo "Creating Docker volume for data persistence..."
docker volume create informatics-postgres-data || true

# Start PostgreSQL container
echo "Starting PostgreSQL container..."
docker run -d \
    --name $CONTAINER_NAME \
    -e POSTGRES_USER=$POSTGRES_USER \
    -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
    -e POSTGRES_DB=$POSTGRES_DB \
    -p $POSTGRES_PORT:5432 \
    -v informatics-postgres-data:/var/lib/postgresql/data \
    postgres:16-alpine

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
sleep 5

# Test connection
for i in {1..30}; do
    if docker exec $CONTAINER_NAME pg_isready -U $POSTGRES_USER &> /dev/null; then
        echo "✓ PostgreSQL is ready!"
        break
    fi
    echo "  Waiting... ($i/30)"
    sleep 1
done

# Verify connection
docker exec $CONTAINER_NAME psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT version();" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "PostgreSQL setup completed successfully!"
    echo "=========================================="
    echo ""
    echo "Connection Details:"
    echo "  Host: localhost"
    echo "  Port: $POSTGRES_PORT"
    echo "  Database: $POSTGRES_DB"
    echo "  User: $POSTGRES_USER"
    echo "  Password: $POSTGRES_PASSWORD"
    echo ""
    echo "To connect via psql:"
    echo "  docker exec -it $CONTAINER_NAME psql -U $POSTGRES_USER -d $POSTGRES_DB"
    echo ""
    echo "To stop the container:"
    echo "  docker stop $CONTAINER_NAME"
    echo ""
    echo "To start the container again:"
    echo "  docker start $CONTAINER_NAME"
    echo ""
    echo "Add these to your .env file:"
    echo "  DATABASE_TYPE=postgresql"
    echo "  POSTGRES_HOST=localhost"
    echo "  POSTGRES_PORT=$POSTGRES_PORT"
    echo "  POSTGRES_USER=$POSTGRES_USER"
    echo "  POSTGRES_PASSWORD=$POSTGRES_PASSWORD"
    echo "  POSTGRES_DB=$POSTGRES_DB"
    echo ""
else
    echo "Error: Failed to connect to PostgreSQL"
    exit 1
fi
