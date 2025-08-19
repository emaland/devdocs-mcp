#!/bin/bash

# Script to update SHA256 hashes in the Homebrew formula
# Run this after creating a GitHub release

set -e

FORMULA_PATH="homebrew/Formula/devdocs-mcp.rb"
VERSION="${1:-0.1.0}"

echo "Updating SHA256 hashes for DevDocs MCP v${VERSION}"
echo "================================================"
echo ""

# Function to get SHA256 of a URL
get_sha256() {
    local url=$1
    local temp_file=$(mktemp)
    
    echo "Downloading: $url"
    if curl -L -s -o "$temp_file" "$url"; then
        local sha=$(shasum -a 256 "$temp_file" | cut -d' ' -f1)
        rm "$temp_file"
        echo "SHA256: $sha"
        echo "$sha"
    else
        echo "Failed to download: $url"
        rm "$temp_file"
        return 1
    fi
}

# Update main formula SHA256
echo "1. Updating main formula SHA256..."
MAIN_URL="https://github.com/emaland/devdocs-mcp/archive/refs/tags/v${VERSION}.tar.gz"

# For now, since the repo doesn't exist yet, we'll create a placeholder
if [[ "$1" == "--local" ]]; then
    echo "Calculating SHA256 for local archive..."
    # Create a temporary archive of the current directory
    TEMP_ARCHIVE=$(mktemp).tar.gz
    tar czf "$TEMP_ARCHIVE" --exclude='.git' --exclude='__pycache__' --exclude='.pytest_cache' --exclude='venv' --exclude='.venv' .
    MAIN_SHA=$(shasum -a 256 "$TEMP_ARCHIVE" | cut -d' ' -f1)
    rm "$TEMP_ARCHIVE"
    echo "Local SHA256: $MAIN_SHA"
else
    echo "Note: Repository must be pushed to GitHub and tagged with v${VERSION}"
    echo "Once tagged, the SHA256 will be:"
    echo ""
    echo "Run: curl -L https://github.com/emaland/devdocs-mcp/archive/refs/tags/v${VERSION}.tar.gz | shasum -a 256"
    echo ""
    MAIN_SHA="PLACEHOLDER_SHA256_RUN_AFTER_GITHUB_RELEASE"
fi

# Update Python package SHA256s
echo ""
echo "2. Getting Python package SHA256s..."

# Get actual SHA256s from PyPI
MCP_SHA=$(get_sha256 "https://files.pythonhosted.org/packages/source/m/mcp/mcp-1.0.0.tar.gz" 2>/dev/null || echo "PLACEHOLDER_MCP_SHA256")
HTTPX_SHA=$(get_sha256 "https://files.pythonhosted.org/packages/source/h/httpx/httpx-0.27.0.tar.gz" 2>/dev/null || echo "PLACEHOLDER_HTTPX_SHA256")
BS4_SHA=$(get_sha256 "https://files.pythonhosted.org/packages/source/b/beautifulsoup4/beautifulsoup4-4.12.3.tar.gz" 2>/dev/null || echo "PLACEHOLDER_BS4_SHA256")

# Update the formula
echo ""
echo "3. Updating formula file..."

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS sed requires -i ''
    sed -i '' "s/sha256 \"PLACEHOLDER_SHA256\"/sha256 \"${MAIN_SHA}\"/" "$FORMULA_PATH"
    sed -i '' "s/sha256 \"PLACEHOLDER_MCP_SHA256\"/sha256 \"${MCP_SHA}\"/" "$FORMULA_PATH"
    sed -i '' "s/sha256 \"PLACEHOLDER_HTTPX_SHA256\"/sha256 \"${HTTPX_SHA}\"/" "$FORMULA_PATH"
    sed -i '' "s/sha256 \"PLACEHOLDER_BS4_SHA256\"/sha256 \"${BS4_SHA}\"/" "$FORMULA_PATH"
else
    # Linux sed
    sed -i "s/sha256 \"PLACEHOLDER_SHA256\"/sha256 \"${MAIN_SHA}\"/" "$FORMULA_PATH"
    sed -i "s/sha256 \"PLACEHOLDER_MCP_SHA256\"/sha256 \"${MCP_SHA}\"/" "$FORMULA_PATH"
    sed -i "s/sha256 \"PLACEHOLDER_HTTPX_SHA256\"/sha256 \"${HTTPX_SHA}\"/" "$FORMULA_PATH"
    sed -i "s/sha256 \"PLACEHOLDER_BS4_SHA256\"/sha256 \"${BS4_SHA}\"/" "$FORMULA_PATH"
fi

echo "Formula updated!"
echo ""
echo "Next steps:"
echo "1. Push your code to GitHub: git push origin main"
echo "2. Create a release tag: git tag v${VERSION} && git push origin v${VERSION}"
echo "3. Run this script again without --local flag to get the real SHA256"
echo "4. Update the formula with the real SHA256"
echo "5. Test locally: brew install --build-from-source homebrew/Formula/devdocs-mcp.rb"
echo "6. Create a homebrew tap repository: homebrew-devdocs-mcp"
echo "7. Push the formula to your tap"