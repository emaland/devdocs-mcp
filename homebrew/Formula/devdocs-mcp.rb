class DevdocsMcp < Formula
  desc "Model Context Protocol server providing AI assistants access to DevDocs documentation"
  homepage "https://github.com/emaland/devdocs-mcp"
  url "https://github.com/emaland/devdocs-mcp/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "fee38e4ebc16df3e211aadd558966540ca98a487a1ed9c581d9da69198597d5e"
  license "MIT"

  depends_on "python@3.12"
  depends_on "uv"

  def install
    # Copy project files
    (libexec/"mcp").install Dir["*"]
    
    # Install dependencies with uv
    cd libexec/"mcp" do
      system "uv", "sync"
    end
    
    # Create wrapper scripts
    (bin/"devdocs-mcp").write <<~EOS
      #!/bin/bash
      cd "#{libexec}/mcp"
      exec uv run python devdocs_mcp_server.py "$@"
    EOS
    
    (bin/"devdocs-mcp-cli").write <<~EOS
      #!/bin/bash
      cd "#{libexec}/mcp"
      exec uv run python scripts/cli.py "$@"
    EOS
    
    (bin/"devdocs-mcp-start").write <<~EOS
      #!/bin/bash
      docker run --name devdocs -d -p 9292:9292 ghcr.io/freecodecamp/devdocs:latest
      echo "DevDocs started at http://localhost:9292"
    EOS
    
    (bin/"devdocs-mcp-stop").write <<~EOS
      #!/bin/bash
      docker stop devdocs
      docker rm devdocs
      echo "DevDocs stopped"
    EOS
    
    (bin/"devdocs-mcp-build").write <<~EOS
      #!/bin/bash
      cd "#{libexec}/mcp"
      exec bash scripts/build-devdocs.sh "$@"
    EOS
    
    chmod 0755, bin/"devdocs-mcp"
    chmod 0755, bin/"devdocs-mcp-cli"
    chmod 0755, bin/"devdocs-mcp-start"
    chmod 0755, bin/"devdocs-mcp-stop"
    chmod 0755, bin/"devdocs-mcp-build"
  end

  def post_install
    ohai "Setting up DevDocs MCP Server..."
    ohai "To configure Claude, run:"
    puts "  claude mcp add devdocs #{bin}/devdocs-mcp"
  end

  def caveats
    <<~EOS
      DevDocs MCP Server has been installed!

      Quick Start:
      1. Start the DevDocs server (requires Docker):
         devdocs-mcp-start

      2. Add to Claude:
         claude mcp add devdocs /usr/local/bin/devdocs-mcp

      3. Test the connection (optional):
         devdocs-mcp-cli list
         devdocs-mcp-cli search svelte component

      Commands:
        devdocs-mcp-start  - Start the DevDocs Docker container
        devdocs-mcp-stop   - Stop the DevDocs Docker container
        devdocs-mcp-build  - Build custom DevDocs with selected documentation
        devdocs-mcp-cli    - CLI tool to test and explore DevDocs
        devdocs-mcp        - MCP server (called by Claude)
      
      Build a custom DevDocs image with only the docs you need:
        devdocs-mcp-build svelte tailwindcss vite
        devdocs-mcp-build --popular
        devdocs-mcp-build --list

      The MCP server connects to DevDocs running at http://localhost:9292
    EOS
  end

  test do
    # Test that the script runs and shows help/version
    system "#{bin}/devdocs-mcp", "--help"
  end
end
