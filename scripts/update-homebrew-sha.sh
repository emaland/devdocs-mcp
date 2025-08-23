#!/bin/bash

# Script to update SHA256 hash in the Homebrew formula
# Run this after creating a GitHub release

set -e

FORMULA_PATH="homebrew/Formula/devdocs-mcp.rb"
VERSION="${1:-0.2.0}"

echo "Updating SHA256 hash for DevDocs MCP v${VERSION}"
echo "================================================"
echo ""

# Update main formula SHA256
echo "Getting SHA256 for release tarball..."
MAIN_URL="https://github.com/emaland/devdocs-mcp/archive/refs/tags/v${VERSION}.tar.gz"

# Check if the release exists
if curl -f -L -s -o /dev/null "$MAIN_URL"; then
    echo "Downloading release tarball..."
    MAIN_SHA=$(curl -L -s "$MAIN_URL" | shasum -a 256 | cut -d' ' -f1)
    echo "SHA256: $MAIN_SHA"
    
    # Update the formula
    echo ""
    echo "Updating formula file..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS sed requires -i ''
        sed -i '' "s/PLACEHOLDER_SHA256_RUN_AFTER_GITHUB_RELEASE/${MAIN_SHA}/" "$FORMULA_PATH"
    else
        # Linux sed
        sed -i "s/PLACEHOLDER_SHA256_RUN_AFTER_GITHUB_RELEASE/${MAIN_SHA}/" "$FORMULA_PATH"
    fi
    
    echo "Formula updated!"
    echo ""
    echo "Next steps:"
    echo "1. Review the changes: git diff $FORMULA_PATH"
    echo "2. Commit the updated formula: git add $FORMULA_PATH && git commit -m 'Update SHA256 for v${VERSION}'"
    echo "3. Push the changes: git push origin main"
    echo "4. Test locally: brew install --build-from-source $FORMULA_PATH"
    echo "5. Create a homebrew tap repository: homebrew-devdocs-mcp"
    echo "6. Copy the formula to your tap and push"
else
    echo "Release not found at: $MAIN_URL"
    echo ""
    echo "To create a release:"
    echo "1. Commit and push all changes: git add . && git commit -m 'Prepare for v${VERSION}' && git push origin main"
    echo "2. Create and push tag: git tag v${VERSION} && git push origin v${VERSION}"
    echo "3. Create GitHub release: gh release create v${VERSION} --generate-notes"
    echo "4. Run this script again to update the SHA256"
fi
