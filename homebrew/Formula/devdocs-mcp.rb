class DevdocsMcp < Formula
  desc "Model Context Protocol server providing AI assistants access to DevDocs documentation"
  homepage "https://github.com/emaland/devdocs-mcp"
  url "https://github.com/emaland/devdocs-mcp/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "2ec13ece5a502fa7c05013796788a6f4032e2cafb34cd2462f97bf802198c5c8"
  license "MIT"

  depends_on "python@3.12"
  depends_on "uv"
  depends_on "pandoc"

  def install
    # Copy project files
    (libexec/"mcp").install Dir["*"]
 
    # Install docker-compose.yml to etc
    etc.install "docker-compose.yml" => "devdocs-mcp/docker-compose.yml"
 
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
      # Use docker-compose if available, otherwise fallback to docker run
      COMPOSE_FILE="#{etc}/devdocs-mcp/docker-compose.yml"
      if [ -f "$COMPOSE_FILE" ]; then
        docker-compose -f "$COMPOSE_FILE" up -d devdocs
      else
        docker run --name devdocs -d -p 9292:9292 ghcr.io/freecodecamp/devdocs:latest
      fi
      echo "DevDocs started at http://localhost:9292"
    EOS
 
    (bin/"devdocs-mcp-stop").write <<~EOS
      #!/bin/bash
      # Use docker-compose if available, otherwise fallback to docker stop
      COMPOSE_FILE="#{etc}/devdocs-mcp/docker-compose.yml"
      if [ -f "$COMPOSE_FILE" ]; then
        docker-compose -f "$COMPOSE_FILE" stop devdocs
        docker-compose -f "$COMPOSE_FILE" rm -f devdocs
      else
        docker stop devdocs
        docker rm devdocs
      fi
      echo "DevDocs stopped"
    EOS
 
    (bin/"devdocs-mcp-build").write <<~EOS
      #!/bin/bash
      cd "#{libexec}/mcp"
      exec bash scripts/build-devdocs.sh "$@"
    EOS

    (bin/"devdocs-mcp-build-custom").write <<~EOS
      #!/bin/bash
      cd "#{libexec}/mcp"
      exec bash scripts/build-with-custom-docsets.sh "$@"
    EOS
 
    chmod 0755, bin/"devdocs-mcp"
    chmod 0755, bin/"devdocs-mcp-cli"
    chmod 0755, bin/"devdocs-mcp-start"
    chmod 0755, bin/"devdocs-mcp-stop"
    chmod 0755, bin/"devdocs-mcp-build"
    chmod 0755, bin/"devdocs-mcp-build-custom"
  end

  def post_install
    ohai "Setting up DevDocs MCP Server..."
    ohai "To configure Claude, run:"
    puts "  claude mcp add --env DEVDOCS_URL=http://localhost:9292 devdocs #{bin}/devdocs-mcp"
  end

  def caveats
    <<~EOS
      DevDocs MCP Server has been installed!

      Quick Start:
      1. Start the DevDocs server (requires Docker):
         devdocs-mcp-start

      2. Add to Claude:
         claude mcp add --env DEVDOCS_URL=http://localhost:9292 devdocs /usr/local/bin/devdocs-mcp

      3. Test the connection (optional):
         devdocs-mcp-cli list
         devdocs-mcp-cli search svelte component

      Commands:
        devdocs-mcp-start        - Start the DevDocs Docker container
        devdocs-mcp-stop         - Stop the DevDocs Docker container
        devdocs-mcp-build        - Build custom DevDocs with selected documentation
        devdocs-mcp-build-custom - Build DevDocs with custom docsets (Skeleton, Tauri)
        devdocs-mcp-cli          - CLI tool to test and explore DevDocs
        devdocs-mcp              - MCP server (called by Claude)
      
      Build a custom DevDocs image with only the docs you need:
        devdocs-mcp-build svelte tailwindcss vite
        devdocs-mcp-build --popular
        devdocs-mcp-build --list

      Build with custom docsets (Skeleton v3, Tauri v2):
        devdocs-mcp-build-custom --with-skeleton --with-tauri svelte
        devdocs-mcp-build-custom --frontend --with-skeleton

      The MCP server connects to DevDocs running at http://localhost:9292
    EOS
  end

  test do
    # Test that the script runs and shows help/version
    system "#{bin}/devdocs-mcp", "--help"
  end
end
