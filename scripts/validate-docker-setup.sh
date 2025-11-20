#!/bin/bash
# Docker Configuration Validation Script

set -e

echo "========================================="
echo "Docker Configuration Validation"
echo "========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is installed${NC}"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose is installed${NC}"

echo ""
echo "Validating configuration files..."

# Check if Dockerfile exists
if [ ! -f "Dockerfile" ]; then
    echo -e "${RED}✗ Dockerfile not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Dockerfile exists${NC}"

# Check if docker-compose.dev.yml exists
if [ ! -f "docker-compose.dev.yml" ]; then
    echo -e "${RED}✗ docker-compose.dev.yml not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ docker-compose.dev.yml exists${NC}"

# Check if docker-compose.prod.yml exists
if [ ! -f "docker-compose.prod.yml" ]; then
    echo -e "${RED}✗ docker-compose.prod.yml not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ docker-compose.prod.yml exists${NC}"

# Check if .dockerignore exists
if [ ! -f ".dockerignore" ]; then
    echo -e "${YELLOW}⚠ .dockerignore not found${NC}"
else
    echo -e "${GREEN}✓ .dockerignore exists${NC}"
fi

# Validate docker-compose.dev.yml
echo ""
echo "Validating docker-compose.dev.yml..."
if docker-compose -f docker-compose.dev.yml config > /dev/null 2>&1; then
    echo -e "${GREEN}✓ docker-compose.dev.yml is valid${NC}"
else
    echo -e "${RED}✗ docker-compose.dev.yml has errors${NC}"
    docker-compose -f docker-compose.dev.yml config
    exit 1
fi

# Validate docker-compose.prod.yml
echo "Validating docker-compose.prod.yml..."
export AUTH_SECRET="test-secret"
export NEXTAUTH_SECRET="test-secret"
export INITIAL_ADMIN_PASSWORD="test-password"
if docker-compose -f docker-compose.prod.yml config > /dev/null 2>&1; then
    echo -e "${GREEN}✓ docker-compose.prod.yml is valid${NC}"
else
    echo -e "${RED}✗ docker-compose.prod.yml has errors${NC}"
    docker-compose -f docker-compose.prod.yml config
    exit 1
fi

# Check Next.js config for standalone output
echo ""
echo "Checking Next.js configuration..."
if grep -q "output.*standalone" next.config.js; then
    echo -e "${GREEN}✓ Next.js standalone output is configured${NC}"
else
    echo -e "${YELLOW}⚠ Next.js standalone output not found in next.config.js${NC}"
fi

# Check Dockerfile stages
echo ""
echo "Checking Dockerfile stages..."
stages=("base" "dependencies" "development" "builder" "runner")
for stage in "${stages[@]}"; do
    if grep -q "FROM .* AS $stage" Dockerfile; then
        echo -e "${GREEN}✓ Stage '$stage' found${NC}"
    else
        echo -e "${RED}✗ Stage '$stage' not found${NC}"
        exit 1
    fi
done

# Summary
echo ""
echo "========================================="
echo -e "${GREEN}All validation checks passed!${NC}"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Development: docker-compose -f docker-compose.dev.yml up --build"
echo "2. Production:  docker-compose -f docker-compose.prod.yml up --build"
echo ""
echo "For more information, see DOCKER.md"
