#!/bin/bash
# scripts/build-docker-images.sh
# Build all Docker images for HFT Trading Platform

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CPP_ROOT="$(cd "$PROJECT_ROOT/../ml-trading-app-cpp" && pwd)"
GO_ROOT="$(cd "$PROJECT_ROOT/../ml-trading-app-go" && pwd)"

echo "================================================================"
echo "HFT Trading Platform - Docker Build Script"
echo "================================================================"
echo "Project Root: $PROJECT_ROOT"
echo "C++ Engine Root: $CPP_ROOT"
echo "Go Backend Root: $GO_ROOT"
echo ""

# Parse arguments
DOCKER_REGISTRY="${1:-local}"
VERSION="${2:-latest}"

if [ "$DOCKER_REGISTRY" != "local" ]; then
    echo "Publishing to: $DOCKER_REGISTRY"
else
    echo "Building locally (not publishing to registry)"
fi

echo ""
echo "================================================================"
echo "Step 1: Building C++ HFT Engine Docker Image"
echo "================================================================"

cd "$CPP_ROOT"

if [ ! -f "Dockerfile.prod" ]; then
    echo "Error: Dockerfile.prod not found in $CPP_ROOT"
    exit 1
fi

echo "Building C++ engine image..."
docker build -f Dockerfile.prod -t hft-engine:$VERSION \
    -t hft-engine:latest \
    --build-arg CMAKE_BUILD_TYPE=Release \
    .

if [ "$DOCKER_REGISTRY" != "local" ]; then
    echo "Tagging for registry..."
    docker tag hft-engine:$VERSION $DOCKER_REGISTRY/hft-engine:$VERSION
    docker tag hft-engine:latest $DOCKER_REGISTRY/hft-engine:latest

    echo "Pushing to registry..."
    docker push $DOCKER_REGISTRY/hft-engine:$VERSION
    docker push $DOCKER_REGISTRY/hft-engine:latest
fi

echo "✓ C++ Engine image built successfully"
echo ""

echo "================================================================"
echo "Step 2: Building Go API Backend Docker Image"
echo "================================================================"

cd "$GO_ROOT"

if [ ! -f "Dockerfile.server" ]; then
    echo "Error: Dockerfile.server not found in $GO_ROOT"
    exit 1
fi

echo "Building Go backend image..."
docker build -f Dockerfile.server -t hft-backend:$VERSION \
    -t hft-backend:latest \
    .

if [ "$DOCKER_REGISTRY" != "local" ]; then
    echo "Tagging and pushing backend image..."
    docker tag hft-backend:$VERSION $DOCKER_REGISTRY/hft-backend:$VERSION
    docker tag hft-backend:latest $DOCKER_REGISTRY/hft-backend:latest
    docker push $DOCKER_REGISTRY/hft-backend:$VERSION
    docker push $DOCKER_REGISTRY/hft-backend:latest
fi

echo "✓ Go Backend image built successfully"
echo ""

echo "================================================================"
echo "Step 3: Building Frontend Docker Image"
echo "================================================================"

if [ -f "$GO_ROOT/Dockerfile.frontend" ]; then
    echo "Building Frontend image..."
    docker build -f "$GO_ROOT/Dockerfile.frontend" -t hft-frontend:$VERSION \
        -t hft-frontend:latest \
        "$GO_ROOT"

    if [ "$DOCKER_REGISTRY" != "local" ]; then
        echo "Tagging and pushing frontend image..."
        docker tag hft-frontend:$VERSION $DOCKER_REGISTRY/hft-frontend:$VERSION
        docker tag hft-frontend:latest $DOCKER_REGISTRY/hft-frontend:latest
        docker push $DOCKER_REGISTRY/hft-frontend:$VERSION
        docker push $DOCKER_REGISTRY/hft-frontend:latest
    fi

    echo "✓ Frontend image built successfully"
else
    echo "⚠ Dockerfile.frontend not found, skipping frontend build"
fi
echo ""

echo "================================================================"
echo "Step 4: Verify Images"
echo "================================================================"

docker images | grep -E "hft-engine|hft-backend|hft-frontend" | grep "$VERSION\|latest"

echo ""
echo "================================================================"
echo "Docker Build Complete!"
echo "================================================================"
echo ""
echo "To start the full stack:"
echo "  cd $PROJECT_ROOT"
echo "  docker-compose up -d"
echo ""
echo "To run integration tests:"
echo "  cd $PROJECT_ROOT"
echo "  pytest tests/test_e2e_real_trading.py -v -s"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "To stop:"
echo "  docker-compose down"
echo ""
