# DevDocs MCP Server

A Model Context Protocol (MCP) stdio process that enables AI assistants like Claude to access your local DevDocs instance via HTTP, providing seamless search and retrieval of technical documentation for hundreds of programming languages, frameworks, and tools.

**Architecture**: This is not an HTTP server - it's a stdio-based process that communicates with Claude using the MCP protocol. The MCP server connects to a separately running DevDocs instance (typically on http://localhost:9292) to fetch documentation.

## Example use (Claude)

> search svelte docs for how to manage state and describe to me what it says

⏺ I'll search the Svelte documentation for information about state management and describe what it says.

⏺ devdocs - search_docs (MCP)(slug: "svelte", query: "state management")
⎿  No matches found for 'state management' in svelte documentation

⏺ devdocs - search_docs (MCP)(slug: "svelte", query: "state")
⎿  Search results for 'state' in svelte:

     • $state [Runes] - path: `$state`
     … +1 line (ctrl+r to expand)

⏺ devdocs - get_doc_content (MCP)(slug: "svelte", path: "$state", format: "text")
⎿ $state On this page $state $state.raw $state.snapshot Passing state into functions Passing state across modules The $state rune allows you to create reactive st
ate, which means that your UI reacts when it changes. <script> let count = $state(0); </script> <button onclick={() => count++}> clicks: {count} </button> Unlik
e other frameworks you may have encountered, there is no API for interacting with state — count is just a number, rather than an object or a function, and you c
… +46 lines (ctrl+r to expand)

⏺ Based on the Svelte documentation, here's what it says about state management:

Svelte State Management with $state Rune

[...]

## Prerequisites

You need DevDocs running locally on port 9292. There are two options:

### Option 1: Quick Start with Pre-built Image (Multi-GB Download)

```bash
docker run --name devdocs -d -p 9292:9292 ghcr.io/freecodecamp/devdocs:latest
```

**Note:** This pulls the official DevDocs image which includes ALL documentation sets (multiple gigabytes).

### Option 2: Build Minimal DevDocs with Selected Docs Only

For a smaller, faster setup with only the documentation you need:

1. **Clone the DevDocs repository:**

   ```bash
   git clone https://github.com/freeCodeCamp/devdocs.git
   cd devdocs
   ```

2. **Modify the DevDocs Dockerfile to include only specific docs:**

   ```dockerfile
   # Edit the DevDocs Dockerfile and change this line:
   - RUN thor docs:download --all && \
   + RUN thor docs:download svelte tailwindcss vite && \
   ```

   You can specify any documentation sets you need. Popular options include:

   - `react vue angular svelte` (frontend frameworks)
   - `python javascript typescript go rust` (languages)
   - `django rails express fastapi` (backend frameworks)
   - `postgresql mongodb redis` (databases)
   - `docker kubernetes terraform` (DevOps)

   Run `thor docs:list` in the DevDocs directory to see all available options.

3. **Build the custom image:**

   ```bash
   # For most systems:
   docker buildx build -t devdocs:latest --load .
   ```

4. **Run your custom DevDocs:**
   ```bash
   docker run --name devdocs -d -p 9292:9292 devdocs:latest
   ```

This approach creates a much smaller image with only the documentation sets you need.

## Setup

### Using Claude Code

1. **Install uv:**

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Set up the project:**

   ```bash
   cd devdocs-mcp
   uv sync
   ```

3. **Ensure DevDocs is running** (see Prerequisites above)

4. **Add MCP server to Claude:**
   ```bash
   # If running from source:
   claude mcp add devdocs /path/to/mcp/devdocs_mcp_server.py
   
   # If installed via Homebrew:
   claude mcp add devdocs /usr/local/bin/devdocs-mcp
   ```

### Using Docker Compose

Run DevDocs in Docker (the MCP server runs as a stdio process through Claude):

```bash
docker-compose up -d
```

**Note**: This starts DevDocs in a container. The MCP server itself runs as a subprocess of Claude, not in Docker.

### CLI Tool

A command-line interface is provided for testing and exploring the MCP endpoints:

```bash
# Using the wrapper script (after running uv sync)
./devdocs list
./devdocs search svelte component
./devdocs interactive

# Or using uv directly
uv run python scripts/cli.py list

# Search in a specific documentation set
uv run python scripts/cli.py search svelte component
uv run python scripts/cli.py search tailwindcss color

# Get content from a documentation page
uv run python scripts/cli.py get svelte introduction
uv run python scripts/cli.py get tailwindcss installation

# Interactive mode for exploration
uv run python scripts/cli.py interactive

# Use different output formats
uv run python scripts/cli.py list --format json
uv run python scripts/cli.py get svelte introduction --format html

# Connect to a different DevDocs instance
uv run python scripts/cli.py --url http://localhost:3000 list
```

### Interactive Mode

The interactive mode provides a REPL-like interface:

```
devdocs> list                    # List all documentation sets
devdocs> slugs                   # Show just the slugs for easy copying
devdocs> search svelte state     # Search for 'state' in Svelte docs
devdocs> get svelte introduction # Get content from a page
devdocs> help                    # Show available commands
devdocs> quit                    # Exit
```

## Development

**Install development dependencies:**

```bash
uv sync --group dev
```

**Run tests:**

```bash
# Run all pytest tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run integration tests only
uv run python tests/test_integration.py

# Run all tests including linting
uv run python scripts/test.py
```

**Code formatting:**

```bash
uv run black .
uv run ruff check .
```

## Available Tools

### `list_docs`

Lists all available documentation sets in the DevDocs instance.

**Example output:**

```
• Svelte (v5.33.11) - slug: `svelte`
• Tailwind CSS (v4.1.11) - slug: `tailwindcss`
• React - slug: `react`
```

### `search_docs`

Search for entries within a specific documentation set.

**Parameters:**

- `slug`: Documentation set identifier (e.g., "svelte", "tailwindcss")
- `query`: Search term to find matching entries

**Example:**

```
search_docs(slug="svelte", query="component")
```

### `get_doc_content`

Retrieve the full content of a specific documentation page.

**Parameters:**

- `slug`: Documentation set identifier
- `path`: Path to the documentation page
- `format`: Return format ("text" or "html", defaults to "text")

**Example:**

```
get_doc_content(slug="svelte", path="introduction", format="text")
```

## Usage with Claude Desktop

### Quick Setup

1. **Ensure DevDocs is running** (see Prerequisites section above for options)

2. **Configure Claude Desktop**:

   Using Claude CLI (recommended):
   ```bash
   # If running from source:
   claude mcp add devdocs /path/to/mcp/devdocs_mcp_server.py
   
   # If installed via Homebrew:
   claude mcp add devdocs /usr/local/bin/devdocs-mcp
   ```

   Or manually edit Claude's config file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

   ```json
   {
     "mcpServers": {
       "devdocs": {
         "command": "uv",
         "args": ["run", "python", "devdocs_mcp_server.py"],
         "cwd": "/path/to/devdocs/mcp",
         "env": {
           "DEVDOCS_URL": "http://localhost:9292"
         }
       }
     }
   }
   ```

3. **Restart Claude Desktop** to load the MCP server.

See [CLAUDE_SETUP.md](./CLAUDE_SETUP.md) for detailed setup instructions and troubleshooting.


## Environment Variables

- `DEVDOCS_URL`: URL of the DevDocs instance (default: http://localhost:9292)

## Quick Start

```bash
# Quick setup with automatic configuration
./scripts/quick-setup.sh

# Or use the install script for more options
./scripts/install.sh
```

## Scripts

All scripts are located in the `scripts/` directory:

- `scripts/quick-setup.sh` - Quick setup with uv and Docker
- `scripts/install.sh` - Installation wizard with multiple options
- `scripts/build-devdocs.sh` - Build custom DevDocs with selected documentation
- `scripts/cli.py` - Interactive CLI for testing MCP endpoints
- `scripts/test.py` - Run all tests including linting
- `scripts/dev.py` - Development helper scripts
- `scripts/update-homebrew-sha.sh` - Update SHA256 hashes for Homebrew formula
- `scripts/run_mcp_server.sh` - Run the MCP server with Docker

The `devdocs` CLI wrapper remains for convenient access to the CLI:

- `./devdocs list` - List available documentation
- `./devdocs search svelte component` - Search documentation
- `./devdocs interactive` - Interactive mode

## Building Custom DevDocs

Instead of downloading the full multi-GB DevDocs image, you can build a custom image with only the documentation you need:

```bash
# Build with specific docs
./scripts/build-devdocs.sh svelte tailwindcss react

# Build with popular documentation sets
./scripts/build-devdocs.sh --popular

# Build with frontend-focused docs
./scripts/build-devdocs.sh --frontend

# List all available documentation sets
./scripts/build-devdocs.sh --list

# Build for specific platform
./scripts/build-devdocs.sh --platform linux/arm64 python django
```

After building, the script will:

1. Create a custom Docker image (e.g., `devdocs:custom`)
2. Optionally update `docker-compose.yml` to use your custom image
3. Allow you to use `devdocs-mcp-start` and `devdocs-mcp-stop` with your custom build

This is especially useful for:

- Reducing disk space (custom builds are much smaller)
- Faster startup times
- Including only relevant documentation for your projects
