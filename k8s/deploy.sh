#!/bin/bash
# k8s/deploy.sh
# Kustomize-based deployment script for HFT Trading Platform

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-dev}"
NAMESPACE="hft-trading"
DRY_RUN="${DRY_RUN:-false}"

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "production" ]]; then
    echo -e "${RED}Error: Invalid environment '$ENVIRONMENT'${NC}"
    echo "Usage: $0 [dev|production]"
    echo "Environment: DRY_RUN=true $0 production (preview only)"
    exit 1
fi

# Print header
echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  HFT Trading Platform - Kustomize Deploy      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Environment: $ENVIRONMENT${NC}"
echo -e "${YELLOW}Namespace: $NAMESPACE${NC}"
echo ""

# Step 1: Check prerequisites
echo -e "${BLUE}Step 1: Checking prerequisites...${NC}"
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl not found${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ kubectl found${NC}"

if ! kubectl version --client &> /dev/null; then
    echo -e "${RED}Error: Cannot connect to kubectl${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ kubectl accessible${NC}"

# Step 2: Build manifests locally
echo ""
echo -e "${BLUE}Step 2: Building manifests from kustomization...${NC}"
if ! MANIFEST=$(kubectl kustomize overlays/$ENVIRONMENT); then
    echo -e "${RED}Error: kustomize build failed${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ kustomize build successful${NC}"

if [[ "$DRY_RUN" == "true" ]]; then
    echo -e "${YELLOW}DRY RUN MODE - Preview only${NC}"
    echo ""
    echo "$MANIFEST" | head -100
    echo ""
    echo -e "${YELLOW}... (output truncated, full manifest available with kubectl kustomize) ...${NC}"
    exit 0
fi

for secret_var in POSTGRES_PASSWORD DATABASE_URL JWT_SECRET; do
    if [[ -z "${!secret_var:-}" ]]; then
        echo -e "${RED}Error: $secret_var must be set for deployment${NC}"
        exit 1
    fi
done

POSTGRES_PASSWORD_B64=$(printf '%s' "$POSTGRES_PASSWORD" | base64 | tr -d '\n')
DATABASE_URL_B64=$(printf '%s' "$DATABASE_URL" | base64 | tr -d '\n')
JWT_SECRET_B64=$(printf '%s' "$JWT_SECRET" | base64 | tr -d '\n')

# Step 3: Create namespace only after local validation succeeds
echo ""
echo -e "${BLUE}Step 3: Ensuring namespace exists...${NC}"
if kubectl get namespace $NAMESPACE > /dev/null 2>&1; then
    echo -e "${GREEN}  ✓ Namespace $NAMESPACE exists${NC}"
else
    echo -e "${YELLOW}  Creating namespace $NAMESPACE...${NC}"
    kubectl create namespace $NAMESPACE
    echo -e "${GREEN}  ✓ Namespace created${NC}"
fi

# Step 4: Apply runtime credentials and rendered manifests
echo ""
echo -e "${BLUE}Step 4: Applying deployment resources...${NC}"
echo -e "${YELLOW}Applying runtime secrets from the environment...${NC}"
kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: postgres-secret
  namespace: $NAMESPACE
type: Opaque
data:
  POSTGRES_PASSWORD: $POSTGRES_PASSWORD_B64
---
apiVersion: v1
kind: Secret
metadata:
  name: backend-secrets
  namespace: $NAMESPACE
type: Opaque
data:
  DATABASE_URL: $DATABASE_URL_B64
  JWT_SECRET: $JWT_SECRET_B64
EOF

echo -e "${YELLOW}Applying manifests...${NC}"
echo "$MANIFEST" | kubectl apply -f -
echo -e "${GREEN}  ✓ Manifests applied${NC}"

# Step 5: Wait for deployments
echo ""
echo -e "${BLUE}Step 5: Waiting for deployments to be ready...${NC}"
DEPLOYMENTS=("hft-backend" "hft-engine" "nginx-ingress")

for deployment in "${DEPLOYMENTS[@]}"; do
    if kubectl get deployment $deployment -n $NAMESPACE > /dev/null 2>&1; then
        echo -e "${YELLOW}  Waiting for $deployment...${NC}"
        kubectl rollout status deployment/$deployment -n $NAMESPACE --timeout=300s
        echo -e "${GREEN}  ✓ $deployment ready${NC}"
    fi
done

# Step 6: Check StatefulSets
echo ""
echo -e "${BLUE}Step 6: Checking StatefulSets...${NC}"
STATEFULSETS=("postgres")

for statefulset in "${STATEFULSETS[@]}"; do
    if kubectl get statefulset $statefulset -n $NAMESPACE > /dev/null 2>&1; then
        echo -e "${YELLOW}  Checking $statefulset...${NC}"
        kubectl rollout status statefulset/$statefulset -n $NAMESPACE --timeout=300s
        echo -e "${GREEN}  ✓ $statefulset ready${NC}"
    fi
done

# Step 7: Show deployment summary
echo ""
echo -e "${BLUE}Step 7: Deployment Summary${NC}"
echo ""
echo -e "${YELLOW}Running services:${NC}"
kubectl get pods -n $NAMESPACE -o wide | grep -v "kube-" || echo "  (initializing...)"

echo ""
echo -e "${YELLOW}Services:${NC}"
kubectl get svc -n $NAMESPACE

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Deployment Complete!                         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"

# Environment-specific info
if [[ "$ENVIRONMENT" == "dev" ]]; then
    echo ""
    echo -e "${YELLOW}Development Environment Info:${NC}"
    echo "  • Single replica of each service (minimal resources)"
    echo "  • Debug logging enabled"
    echo "  • Local image pull (imagePullPolicy: Never)"
    echo ""
    echo -e "${YELLOW}Access Services:${NC}"
    echo "  kubectl port-forward svc/nginx-ingress 8080:80 -n $NAMESPACE"
    echo "  Then visit: http://localhost:8080"
else
    echo ""
    echo -e "${YELLOW}Production Environment Info:${NC}"
    echo "  • 4 replicas of backend (high availability)"
    echo "  • Info logging level"
    echo "  • Production resource limits"
    echo "  • Monitoring enabled (Prometheus annotations)"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "  • Monitor with: kubectl logs -f deployment/hft-backend -n $NAMESPACE"
    echo "  • Check status: kubectl get all -n $NAMESPACE"
    echo "  • Configure ingress for external access"
fi

echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  # View all resources"
echo "  kubectl get all -n $NAMESPACE"
echo ""
echo "  # View logs"
echo "  kubectl logs -f deployment/hft-backend -n $NAMESPACE"
echo ""
echo "  # Delete deployment"
echo "  kubectl delete namespace $NAMESPACE"
echo ""
