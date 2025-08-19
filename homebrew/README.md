# Homebrew Tap for DevDocs MCP Server

This is a Homebrew tap for installing the DevDocs MCP Server - a stdio-based process that enables Claude to access DevDocs documentation.

## Installation

### Method 1: Using the tap

```bash
# Add the tap
brew tap emaland/devdocs-mcp

# Install the formula
brew install emaland/devdocs-mcp/devdocs-mcp
```

### Method 2: Direct installation

```bash
brew install emaland/devdocs-mcp/devdocs-mcp
```

## Usage

After installation:

1. Start the DevDocs server:
   ```bash
   devdocs-mcp-start
   ```

2. Add to Claude:
   ```bash
   claude mcp add devdocs /usr/local/bin/devdocs-mcp
   ```

3. Test the connection (optional):
   ```bash
   devdocs-mcp-cli list
   devdocs-mcp-cli search svelte component
   ```

4. Restart Claude to load the new MCP server

## Commands

- `devdocs-mcp` - Run the MCP stdio process (automatically called by Claude as a subprocess)
- `devdocs-mcp-cli` - CLI tool to test and explore DevDocs
- `devdocs-mcp-start` - Start the DevDocs server Docker container
- `devdocs-mcp-stop` - Stop the DevDocs server Docker container
- `devdocs-mcp-build` - Build custom DevDocs with selected documentation

## Features

- Access to 600+ documentation sets including:
  - Programming languages (Python, JavaScript, Go, Rust, etc.)
  - Web frameworks (React, Vue, Svelte, Django, Rails, etc.)
  - Databases (PostgreSQL, MongoDB, Redis, etc.)
  - DevOps tools (Docker, Kubernetes, Terraform, etc.)
  - And many more!

- MCP tools provided:
  - `list_docs` - List all available documentation sets
  - `search_docs` - Search within a specific documentation set
  - `get_doc_content` - Retrieve full documentation content

## Requirements

- Python 3.10+
- Docker (for running the DevDocs documentation server)
- uv (Python package manager, installed as a dependency)

## Author

Eric Maland (eric@instantcocoa.com)

## License

MIT
