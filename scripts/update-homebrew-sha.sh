#!/bin/bash

# Script to update SHA256 hash and version in the Homebrew formula
# Automatically detects version from pyproject.toml and updates the formula

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
FORMULA_PATH="$PROJECT_DIR/homebrew/Formula/devdocs-mcp.rb"
PYPROJECT_PATH="$PROJECT_DIR/pyproject.toml"

# Extract version from pyproject.toml
if [ ! -f "$PYPROJECT_PATH" ]; then
    echo "Error: pyproject.toml not found at $PYPROJECT_PATH"
    exit 1
fi

VERSION=$(grep '^version = ' "$PYPROJECT_PATH" | sed 's/version = "\(.*\)"/\1/')

if [ -z "$VERSION" ]; then
    echo "Error: Could not extract version from pyproject.toml"
    exit 1
fi

echo "Updating Homebrew formula for DevDocs MCP v${VERSION}"
echo "================================================"
echo ""

# Update version in formula
echo "Updating version in formula to v${VERSION}..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS sed requires -i ''
    sed -i '' "s|url \"https://github.com/emaland/devdocs-mcp/archive/refs/tags/v[0-9.]*\.tar\.gz\"|url \"https://github.com/emaland/devdocs-mcp/archive/refs/tags/v${VERSION}.tar.gz\"|" "$FORMULA_PATH"
else
    # Linux sed
    sed -i "s|url \"https://github.com/emaland/devdocs-mcp/archive/refs/tags/v[0-9.]*\.tar\.gz\"|url \"https://github.com/emaland/devdocs-mcp/archive/refs/tags/v${VERSION}.tar.gz\"|" "$FORMULA_PATH"
fi

# Calculate SHA256 for release tarball
echo "Getting SHA256 for release tarball..."
MAIN_URL="https://github.com/emaland/devdocs-mcp/archive/refs/tags/v${VERSION}.tar.gz"

# Check if the release exists
if curl -f -L -s -o /dev/null "$MAIN_URL"; then
    echo "Downloading release tarball..."
    MAIN_SHA=$(curl -L -s "$MAIN_URL" | shasum -a 256 | cut -d' ' -f1)
    echo "SHA256: $MAIN_SHA"
    
    # Update the SHA256 in the formula
    echo ""
    echo "Updating SHA256 in formula..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS sed requires -i ''
        sed -i '' "s/sha256 \"[a-f0-9]*\"/sha256 \"${MAIN_SHA}\"/" "$FORMULA_PATH"
    else
        # Linux sed
        sed -i "s/sha256 \"[a-f0-9]*\"/sha256 \"${MAIN_SHA}\"/" "$FORMULA_PATH"
    fi
    
    echo "Formula updated!"
    echo ""
    echo "Changes made:"
    echo "- Version: v${VERSION}"
    echo "- SHA256: ${MAIN_SHA}"
    echo ""
    echo "Next steps:"
    echo "1. Review the changes: git diff $FORMULA_PATH"
    echo "2. Commit the updated formula: git add $FORMULA_PATH && git commit -m 'Update Homebrew formula to v${VERSION}'"
    echo "3. Push the changes: git push origin main"
    echo "4. Test locally: brew install --build-from-source $FORMULA_PATH"
    echo "5. Create/update homebrew tap repository: homebrew-devdocs-mcp"
    echo "6. Copy the formula to your tap and push"
else
    echo "Release not found at: $MAIN_URL"
    echo ""
    echo "The formula has been updated with version v${VERSION}, but the SHA256 could not be calculated."
    echo ""
    echo "To create a release and complete the update:"
    echo "1. Commit and push all changes: git add . && git commit -m 'Prepare for v${VERSION}' && git push origin main"
    echo "2. Create and push tag: git tag v${VERSION} && git push origin v${VERSION}"
    echo "3. Create GitHub release: gh release create v${VERSION} --generate-notes"
    echo "4. Run this script again to update the SHA256"
fi