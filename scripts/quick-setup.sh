#!/bin/bash

# Quick setup script for DevDocs MCP Server
set -e

echo "DevDocs MCP Server - Quick Setup"
echo "================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if uv is installed
if ! command -v uv >/dev/null 2>&1; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
fi

# Install dependencies
echo "Setting up project with uv..."
uv sync

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${YELLOW}Warning: Docker is not running. Please start Docker Desktop.${NC}"
    echo "DevDocs requires Docker to run locally."
    exit 1
fi

# Check if DevDocs is already running
if docker ps | grep -q devdocs; then
    echo -e "${GREEN}DevDocs is already running${NC}"
else
    echo "Starting DevDocs..."
    
    # Ask user which option they prefer
    echo ""
    echo "How would you like to run DevDocs?"
    echo "1) Use pre-built image (multi-GB download, all docs)"
    echo "2) I have a custom build ready"
    echo ""
    read -p "Enter your choice (1-2): " choice
    
    case $choice in
        1)
            echo "Starting DevDocs with pre-built image..."
            docker run --name devdocs -d -p 9292:9292 ghcr.io/freecodecamp/devdocs:latest
            ;;
        2)
            echo "Starting DevDocs with custom image..."
            docker run --name devdocs -d -p 9292:9292 devdocs:latest
            ;;
        *)
            echo -e "${RED}Invalid choice. Please run Docker manually.${NC}"
            ;;
    esac
fi

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "DevDocs is running at: http://localhost:9292"
echo ""
echo "To test the MCP server:"
echo "  uv run python scripts/cli.py list"
echo "  uv run python scripts/cli.py interactive"
echo ""
echo "To run the MCP server:"
echo "  uv run python devdocs_mcp_server.py"
echo ""
echo "To use with Claude, add to your claude_config.json:"
echo '  {
    "mcpServers": {
      "devdocs": {
        "command": "uv",
        "args": ["run", "python", "devdocs_mcp_server.py"],
        "cwd": "'$(pwd)'",
        "env": {
          "DEVDOCS_URL": "http://localhost:9292"
        }
      }
    }
  }'