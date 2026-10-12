#!/bin/bash
# scripts/setup_test_db.sh
# Setup PostgreSQL test database and create schema

set -e

: "${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD before setting up the test database}"

echo "Setting up test database..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
for i in {1..30}; do
  if pg_isready -h localhost -U trading_user > /dev/null 2>&1; then
    echo "PostgreSQL is ready"
    break
  fi
  echo "Attempt $i/30 - PostgreSQL not ready yet, waiting..."
  sleep 1
done

# Create test database (idempotent for repeated make setup / test runs)
echo "Creating test database..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U trading_user -d trading_db -v ON_ERROR_STOP=1 <<'EOF'
SELECT 'CREATE DATABASE trading_db_test'
WHERE NOT EXISTS (
  SELECT FROM pg_database WHERE datname = 'trading_db_test'
)\gexec
EOF

echo "Test database setup complete!"
echo ""
echo "To run tests:"
echo "  cd hft-trading-platform"
echo "  python -m pytest tests/ -v"
