#!/usr/bin/env python3
"""
Development runner for DevDocs MCP Server
"""

import subprocess
import sys


def main():
    """Run the MCP server in development mode."""
    try:
        subprocess.run([
            sys.executable, "-m", "devdocs_mcp_server"
        ], check=True)
    except KeyboardInterrupt:
        print("\nShutting down DevDocs MCP Server...")
    except subprocess.CalledProcessError as e:
        print(f"Error running MCP server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()