#!/bin/bash

# DevDocs Custom Build Script
# Builds a minimal DevDocs image with only specified documentation sets

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DEVDOCS_REPO="https://github.com/freeCodeCamp/devdocs.git"
BUILD_DIR="/tmp/devdocs-build-$$"
IMAGE_NAME="devdocs:custom"
SELECTED_DOCS=""
PLATFORM=""

# Function to display usage
usage() {
    echo "DevDocs Custom Builder"
    echo ""
    echo "Usage: $0 [options] [doc1] [doc2] ..."
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -l, --list              List all available documentation sets"
    echo "  -p, --platform PLATFORM Build for specific platform (linux/amd64, linux/arm64)"
    echo "  -i, --image NAME        Docker image name (default: devdocs:custom)"
    echo "  -d, --dir PATH          Build directory (default: /tmp/devdocs-build-\$\$)"
    echo "  --popular               Build with popular docs (react, python, javascript, etc.)"
    echo "  --minimal               Build with minimal set (just svelte and tailwindcss)"
    echo "  --frontend              Build with frontend docs (react, vue, angular, svelte, etc.)"
    echo "  --backend               Build with backend docs (python, node, django, rails, etc.)"
    echo "  --all                   Build with ALL documentation (warning: very large!)"
    echo ""
    echo "Examples:"
    echo "  $0 svelte tailwindcss              # Build with just Svelte and Tailwind"
    echo "  $0 --popular                       # Build with popular documentation sets"
    echo "  $0 --platform linux/arm64 react    # Build for Apple Silicon with React"
    echo "  $0 -l                               # List all available docs"
    echo ""
    exit 0
}

# Function to list available docs
list_docs() {
    echo -e "${BLUE}Fetching available documentation sets...${NC}"
    
    # Clone repo temporarily just to get the list
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    git clone --depth 1 "$DEVDOCS_REPO" devdocs >/dev/null 2>&1
    cd devdocs
    
    echo -e "${GREEN}Available documentation sets:${NC}"
    echo ""
    
    # Use Thor to list docs if available
    if command -v ruby >/dev/null 2>&1; then
        bundle install --quiet >/dev/null 2>&1 || true
        thor docs:list 2>/dev/null | grep -E '^\s+\w+' | sed 's/^[[:space:]]*/  /' || {
            echo "Could not fetch list. Some common options:"
            echo ""
            echo "Languages: python, javascript, typescript, go, rust, ruby, php, java, c, cpp"
            echo "Frontend: react, vue, angular, svelte, nextjs, nuxt, gatsby"
            echo "CSS: css, sass, tailwindcss, bootstrap"
            echo "Backend: django, rails, express, fastapi, spring"
            echo "Databases: postgresql, mysql, mongodb, redis, sqlite"
            echo "Tools: docker, kubernetes, git, npm, webpack, vite"
        }
    else
        echo "Ruby not installed. Here are some common documentation sets:"
        echo ""
        echo "Languages: python, javascript, typescript, go, rust, ruby, php, java, c, cpp"
        echo "Frontend: react, vue, angular, svelte, nextjs, nuxt, gatsby"
        echo "CSS: css, sass, tailwindcss, bootstrap"
        echo "Backend: django, rails, express, fastapi, spring"
        echo "Databases: postgresql, mysql, mongodb, redis, sqlite"
        echo "Tools: docker, kubernetes, git, npm, webpack, vite"
    fi
    
    # Cleanup
    cd /
    rm -rf "$TEMP_DIR"
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -l|--list)
            list_docs
            ;;
        -p|--platform)
            PLATFORM="$2"
            shift 2
            ;;
        -i|--image)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -d|--dir)
            BUILD_DIR="$2"
            shift 2
            ;;
        --popular)
            SELECTED_DOCS="python javascript typescript react vue svelte nodejs express django postgresql docker git css html"
            shift
            ;;
        --minimal)
            SELECTED_DOCS="svelte tailwindcss"
            shift
            ;;
        --frontend)
            SELECTED_DOCS="javascript typescript react vue angular svelte nextjs nuxt gatsby jquery css sass tailwindcss bootstrap html"
            shift
            ;;
        --backend)
            SELECTED_DOCS="python nodejs express django rails fastapi spring postgresql mysql mongodb redis docker"
            shift
            ;;
        --all)
            SELECTED_DOCS="ALL"
            shift
            ;;
        -*)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
        *)
            SELECTED_DOCS="$SELECTED_DOCS $1"
            shift
            ;;
    esac
done

# If no docs selected, show usage
if [ -z "$SELECTED_DOCS" ]; then
    echo -e "${RED}Error: No documentation sets specified${NC}"
    echo ""
    usage
fi

# Detect platform if not specified
if [ -z "$PLATFORM" ]; then
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
        PLATFORM="linux/arm64"
    else
        PLATFORM="linux/amd64"
    fi
    echo -e "${BLUE}Auto-detected platform: $PLATFORM${NC}"
fi

# Confirm with user
echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}DevDocs Custom Build Configuration${NC}"
echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Documentation sets: $SELECTED_DOCS"
echo "Platform: $PLATFORM"
echo "Image name: $IMAGE_NAME"
echo "Build directory: $BUILD_DIR"
echo ""
read -p "Proceed with build? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Build cancelled"
    exit 0
fi

# Create build directory
echo -e "${BLUE}Creating build directory...${NC}"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Clone DevDocs repository
echo -e "${BLUE}Cloning DevDocs repository...${NC}"
git clone "$DEVDOCS_REPO" devdocs
cd devdocs

# Modify Dockerfile
echo -e "${BLUE}Customizing Dockerfile...${NC}"

if [ "$SELECTED_DOCS" = "ALL" ]; then
    echo -e "${YELLOW}Building with ALL documentation (this will be large!)${NC}"
    # Keep the original Dockerfile as-is
else
    # Create backup
    cp Dockerfile Dockerfile.backup
    
    # Replace the thor docs:download line
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS sed
        sed -i '' "s/RUN thor docs:download --all/# RUN thor docs:download --all\nRUN thor docs:download $SELECTED_DOCS/" Dockerfile
    else
        # Linux sed
        sed -i "s/RUN thor docs:download --all/# RUN thor docs:download --all\nRUN thor docs:download $SELECTED_DOCS/" Dockerfile
    fi
    
    echo -e "${GREEN}Modified Dockerfile to build with: $SELECTED_DOCS${NC}"
fi

# Build the Docker image
echo -e "${BLUE}Building Docker image...${NC}"
echo -e "${YELLOW}This may take several minutes...${NC}"

if command -v docker buildx >/dev/null 2>&1; then
    # Use buildx for better platform support
    docker buildx build --platform "$PLATFORM" -t "$IMAGE_NAME" --load .
else
    # Fallback to regular docker build
    docker build -t "$IMAGE_NAME" .
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Build successful!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Docker image created: $IMAGE_NAME"
    echo ""
    echo "To use this image with DevDocs MCP:"
    echo ""
    echo "1. Stop any existing DevDocs container:"
    echo "   devdocs-mcp-stop"
    echo ""
    echo "2. Start your custom build:"
    echo "   docker run --name devdocs -d -p 9292:9292 $IMAGE_NAME"
    echo ""
    echo "3. The MCP server will automatically connect to it"
    echo ""
    echo "To make this permanent, update docker-compose.yml to use: $IMAGE_NAME"
    
    # Offer to update docker-compose.yml
    echo ""
    read -p "Would you like to update docker-compose.yml to use this image? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Find docker-compose.yml - try multiple locations
        # Get the absolute path to the script directory
        if [[ -n "${BASH_SOURCE[0]}" ]]; then
            SCRIPT_PATH="${BASH_SOURCE[0]}"
        else
            SCRIPT_PATH="$0"
        fi
        
        # Get absolute directory path, handling both ./scripts/foo and /full/path cases
        if [[ "$SCRIPT_PATH" = /* ]]; then
            # Absolute path
            SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
        else
            # Relative path - resolve from current directory
            SCRIPT_DIR="$(cd "$(pwd)/$(dirname "$SCRIPT_PATH")" 2>/dev/null && pwd)"
        fi
        
        # Get project directory (parent of scripts)
        if [[ -n "$SCRIPT_DIR" ]]; then
            PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
        else
            PROJECT_DIR="$(pwd)"
        fi
        
        # Try multiple locations for docker-compose.yml
        COMPOSE_PATHS=(
            "$PROJECT_DIR/docker-compose.yml"
            "./docker-compose.yml"
            "$(pwd)/docker-compose.yml"
            "/usr/local/etc/devdocs-mcp/docker-compose.yml"
            "$HOME/.devdocs-mcp/docker-compose.yml"
            "/usr/local/Cellar/devdocs-mcp/*/libexec/mcp/docker-compose.yml"
        )
        
        COMPOSE_FILE=""
        for path in "${COMPOSE_PATHS[@]}"; do
            if [ -f "$path" ]; then
                COMPOSE_FILE="$path"
                echo -e "${BLUE}Found docker-compose.yml at: $path${NC}"
                break
            fi
        done
        
        if [ -n "$COMPOSE_FILE" ]; then
            # Backup original
            cp "$COMPOSE_FILE" "$COMPOSE_FILE.backup"
            echo -e "${BLUE}Created backup: $COMPOSE_FILE.backup${NC}"
            
            # Update image name for the devdocs service specifically
            # This is more precise than replacing all image: lines
            if [[ "$OSTYPE" == "darwin"* ]]; then
                # macOS sed - update the devdocs service image
                sed -i '' "/^  devdocs:/,/^  [^ ]/ s|image:.*|image: $IMAGE_NAME|" "$COMPOSE_FILE"
            else
                # Linux sed
                sed -i "/^  devdocs:/,/^  [^ ]/ s|image:.*|image: $IMAGE_NAME|" "$COMPOSE_FILE"
            fi
            
            echo -e "${GREEN}✅ Updated $COMPOSE_FILE${NC}"
            echo -e "${GREEN}The devdocs service now uses: $IMAGE_NAME${NC}"
            echo ""
            echo "You can now use:"
            echo "  devdocs-mcp-start  - Start your custom DevDocs"
            echo "  devdocs-mcp-stop   - Stop DevDocs"
        else
            echo -e "${YELLOW}⚠️  Could not find docker-compose.yml to update${NC}"
            echo ""
            echo "To use your custom image manually:"
            echo "  docker run --name devdocs -d -p 9292:9292 $IMAGE_NAME"
        fi
    fi
else
    echo -e "${RED}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}❌ Build failed${NC}"
    echo -e "${RED}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Check the error messages above for details"
    exit 1
fi

# Cleanup option
echo ""
read -p "Remove build directory? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Cleaning up...${NC}"
    cd /
    rm -rf "$BUILD_DIR"
    echo -e "${GREEN}Build directory removed${NC}"
fi

echo ""
echo -e "${GREEN}Done!${NC}"