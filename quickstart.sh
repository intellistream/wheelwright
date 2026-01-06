#!/bin/bash
# Quickstart script for SAGE monorepo projects
# helper to install sage-pypi-publisher hooks

set -e

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🚀 Initializing SAGE development environment...${NC}"

# Ensure sage-pypi-publisher is installed
if ! command -v sage-pypi-publisher &> /dev/null; then
    echo -e "${CYAN}📦 Installing sage-pypi-publisher...${NC}"
    pip install sage-pypi-publisher
fi

# Install hooks
echo -e "${CYAN}🪝 Installing git hooks...${NC}"
sage-pypi-publisher install-hooks .

echo -e "${GREEN}✅ Setup complete! Git hooks (pre-commit, pre-push) are active.${NC}"
