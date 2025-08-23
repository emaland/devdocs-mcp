#!/usr/bin/env python3
"""
DevDocs MCP Server

Provides access to DevDocs documentation sets via Model Context Protocol (MCP).
This server runs as a stdio process that Claude (or other MCP clients) communicate with.
It connects to a running DevDocs instance (typically via Docker) to search and retrieve documentation.

Note: This is not an HTTP server - it communicates via stdio with the MCP client (Claude).
"""

import asyncio
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from mcp.server import Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)


class DevDocsClient:
    """Client for interacting with DevDocs API."""
    
    def __init__(self, base_url: str = None):
        if base_url is None:
            base_url = os.getenv("DEVDOCS_URL", "http://localhost:9292")
        self.base_url = base_url
        self._client: Optional[httpx.AsyncClient] = None
        self._docs_cache: Optional[List[Dict[str, Any]]] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def get_available_docs(self) -> List[Dict[str, Any]]:
        """Get list of all available documentation sets."""
        if self._docs_cache is None:
            response = await self.client.get(f"{self.base_url}/docs.json", follow_redirects=True)
            response.raise_for_status()
            self._docs_cache = response.json()
        return self._docs_cache
    
    async def get_doc_index(self, slug: str) -> Dict[str, Any]:
        """Get the index/entries for a specific documentation set."""
        response = await self.client.get(f"{self.base_url}/docs/{slug}/index.json")
        response.raise_for_status()
        return response.json()
    
    async def search_doc_entries(self, slug: str, query: str) -> List[Dict[str, Any]]:
        """Search entries within a specific documentation set."""
        index = await self.get_doc_index(slug)
        entries = index.get("entries", [])
        
        query_lower = query.lower()
        matches = []
        
        for entry in entries:
            name = entry.get("name", "").lower()
            if query_lower in name:
                matches.append(entry)
        
        # Sort by relevance (exact matches first, then prefix matches)
        def sort_key(entry):
            name = entry.get("name", "").lower()
            if name == query_lower:
                return (0, name)
            elif name.startswith(query_lower):
                return (1, name)
            else:
                return (2, name)
        
        return sorted(matches, key=sort_key)[:20]  # Limit to top 20 results
    
    async def get_doc_content(self, slug: str, path: str) -> str:
        """Get the HTML content for a specific documentation page."""
        # DevDocs serves documentation fragments at /docs/{slug}/{path}.html
        url = f"{self.base_url}/docs/{slug}/{path}.html"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.text
    
    async def extract_text_content(self, html: str) -> str:
        """Extract clean text content from HTML using pandoc."""
        try:
            # Try to use the advanced cleaner with pandoc
            from scripts.clean_docs import DocsCleaner
            cleaner = DocsCleaner()
            # Return clean Markdown for better readability
            markdown = cleaner.clean_html(html, preserve_structure=False)
            if markdown and markdown.strip():
                return markdown
        except ImportError:
            pass
        
        # Fallback: Try pandoc directly
        try:
            import subprocess
            result = subprocess.run(
                ['pandoc', '-f', 'html', '-t', 'gfm', '--wrap=none'],
                input=html,
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            if result.stdout:
                return result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Final fallback: Basic HTML extraction
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text and clean it up
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    async def extract_page_info(self, html: str) -> Dict[str, Any]:
        """Extract title and section headings from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract title
        title = None
        # Try different title selectors in order of preference
        title_selectors = ['h1', 'title', '.page-title', '.doc-title', '.main-title']
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.get_text(strip=True):
                title = title_elem.get_text(strip=True)
                break
        
        # Extract section headings (h2, h3, h4)
        sections = []
        for heading in soup.find_all(['h2', 'h3', 'h4', 'h5', 'h6']):
            text = heading.get_text(strip=True)
            if text:
                level = int(heading.name[1])  # Extract number from h1, h2, etc.
                heading_id = heading.get('id', '')
                sections.append({
                    'text': text,
                    'level': level,
                    'id': heading_id
                })
        
        return {
            'title': title,
            'sections': sections
        }
    
    async def list_all_docset_pages(self, slug: str, include_sections: bool = True) -> List[Dict[str, Any]]:
        """List all pages in a docset with their titles and sections."""
        try:
            # Get the index to find all entries
            index = await self.get_doc_index(slug)
            entries = index.get("entries", [])
            
            pages = []
            
            # Process each entry to get page info
            for entry in entries:
                path = entry.get('path', '')
                name = entry.get('name', '')
                entry_type = entry.get('type', '')
                
                page_info = {
                    'name': name,
                    'path': path,
                    'type': entry_type,
                    'title': None,
                    'sections': []
                }
                
                if include_sections and path:
                    try:
                        # Get the HTML content for this page
                        html_content = await self.get_doc_content(slug, path)
                        page_details = await self.extract_page_info(html_content)
                        page_info['title'] = page_details['title']
                        page_info['sections'] = page_details['sections']
                    except Exception as e:
                        # If we can't get page content, continue with basic info
                        page_info['error'] = f"Could not fetch content: {str(e)}"
                
                pages.append(page_info)
            
            return pages
            
        except Exception as e:
            raise Exception(f"Failed to list pages for {slug}: {str(e)}")
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


# Initialize the MCP server
app = Server("devdocs-server")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="list_docs",
            description="List all available documentation sets in DevDocs",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="search_docs",
            description="Search for entries within a specific documentation set",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {
                        "type": "string",
                        "description": "Documentation set slug (e.g., 'svelte', 'tailwindcss', 'react')"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query to find matching entries"
                    }
                },
                "required": ["slug", "query"]
            }
        ),
        Tool(
            name="get_doc_content",
            description="Get the full content of a specific documentation page",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {
                        "type": "string",
                        "description": "Documentation set slug (e.g., 'svelte', 'tailwindcss')"
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to the specific documentation page"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["html", "text"],
                        "description": "Return format: 'html' for raw HTML or 'text' for extracted text",
                        "default": "text"
                    }
                },
                "required": ["slug", "path"]
            }
        ),
        Tool(
            name="list_docset_pages",
            description="List all pages, titles, and sections for a specific documentation set",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {
                        "type": "string",
                        "description": "Documentation set slug (e.g., 'svelte', 'tailwindcss', 'tauri_v2')"
                    },
                    "include_sections": {
                        "type": "boolean",
                        "description": "Whether to include section headings for each page (default: true)",
                        "default": True
                    }
                },
                "required": ["slug"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent]:
    """Handle tool calls."""
    # Create a new client for each call to avoid event loop issues
    devdocs = DevDocsClient()
    
    if name == "list_docs":
        try:
            docs = await devdocs.get_available_docs()
            
            # Format the documentation list
            result = "Available Documentation Sets:\n\n"
            for doc in docs:
                name = doc.get('name', 'Unknown')
                slug = doc.get('slug', 'unknown')
                version = doc.get('version', '')
                version_str = f" (v{version})" if version else ""
                result += f"• {name}{version_str} - slug: `{slug}`\n"
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error listing docs: {str(e)}")]
    
    elif name == "search_docs":
        slug = arguments.get("slug")
        query = arguments.get("query")
        
        if not slug or not query:
            return [TextContent(type="text", text="Error: Both 'slug' and 'query' are required")]
        
        try:
            matches = await devdocs.search_doc_entries(slug, query)
            
            if not matches:
                return [TextContent(type="text", text=f"No matches found for '{query}' in {slug} documentation")]
            
            result = f"Search results for '{query}' in {slug}:\n\n"
            for entry in matches:
                name = entry.get('name', 'Unknown')
                path = entry.get('path', '')
                entry_type = entry.get('type', '')
                type_str = f" [{entry_type}]" if entry_type else ""
                result += f"• {name}{type_str} - path: `{path}`\n"
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error searching {slug}: {str(e)}")]
    
    elif name == "get_doc_content":
        slug = arguments.get("slug")
        path = arguments.get("path")
        format_type = arguments.get("format", "text")
        
        if not slug or not path:
            return [TextContent(type="text", text="Error: Both 'slug' and 'path' are required")]
        
        try:
            html_content = await devdocs.get_doc_content(slug, path)
            
            if format_type == "html":
                return [TextContent(type="text", text=html_content)]
            else:
                text_content = await devdocs.extract_text_content(html_content)
                return [TextContent(type="text", text=text_content)]
                
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting content for {slug}/{path}: {str(e)}")]
    
    elif name == "list_docset_pages":
        slug = arguments.get("slug")
        include_sections = arguments.get("include_sections", True)
        
        if not slug:
            return [TextContent(type="text", text="Error: 'slug' parameter is required")]
        
        try:
            pages = await devdocs.list_all_docset_pages(slug, include_sections)
            
            if not pages:
                return [TextContent(type="text", text=f"No pages found for docset '{slug}'")]
            
            result = f"Pages in {slug} documentation ({len(pages)} total):\n\n"
            
            for page in pages:
                name = page.get('name', 'Unknown')
                path = page.get('path', '')
                title = page.get('title', '')
                page_type = page.get('type', '')
                sections = page.get('sections', [])
                error = page.get('error', '')
                
                # Format the page entry
                type_str = f" [{page_type}]" if page_type else ""
                title_str = f" - {title}" if title and title != name else ""
                result += f"📄 {name}{type_str}{title_str}\n"
                result += f"   Path: {path}\n"
                
                if error:
                    result += f"   ⚠️ {error}\n"
                elif include_sections and sections:
                    result += f"   Sections ({len(sections)}):\n"
                    for section in sections[:10]:  # Limit to first 10 sections
                        level = section.get('level', 2)
                        text = section.get('text', '')
                        indent = "  " * (level - 1)
                        result += f"   {indent}• {text}\n"
                    if len(sections) > 10:
                        result += f"   ... and {len(sections) - 10} more sections\n"
                
                result += "\n"
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error listing pages for {slug}: {str(e)}")]
    
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def startup_info():
    """Display verbose startup information about the MCP server."""
    import sys
    
    print("=" * 80, file=sys.stderr)
    print("DevDocs MCP Server Starting", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print("", file=sys.stderr)
    
    # Server info
    print("📚 DevDocs MCP Server v0.1.0", file=sys.stderr)
    print("Author: Eric Maland (eric@instantcocoa.com)", file=sys.stderr)
    print("", file=sys.stderr)
    
    # Check DevDocs connection
    devdocs_url = os.getenv("DEVDOCS_URL", "http://localhost:9292")
    print(f"🔗 Connecting to DevDocs at: {devdocs_url}", file=sys.stderr)
    
    client = DevDocsClient(devdocs_url)
    available_docs = []
    try:
        # Test connection and get available docs
        docs = await client.get_available_docs()
        available_docs = docs  # Store for later use in examples
        print(f"✅ Successfully connected to DevDocs", file=sys.stderr)
        print(f"📖 Found {len(docs)} documentation sets available:", file=sys.stderr)
        print("", file=sys.stderr)
        
        # Display available documentation sets
        print("Available Documentation Sets:", file=sys.stderr)
        print("-" * 40, file=sys.stderr)
        
        # Create categorized lists with full doc info
        languages = []
        frameworks = []
        databases = []
        tools = []
        other = []
        
        # Extended category mappings
        lang_keywords = ['python', 'javascript', 'typescript', 'go', 'rust', 'java', 'c', 'cpp', 'c++', 
                        'ruby', 'php', 'swift', 'kotlin', 'scala', 'elixir', 'erlang', 'haskell', 
                        'r', 'julia', 'perl', 'lua', 'dart', 'crystal', 'nim', 'ocaml', 'clojure']
        
        framework_keywords = ['react', 'vue', 'angular', 'svelte', 'django', 'rails', 'express', 
                             'fastapi', 'flask', 'spring', 'laravel', 'symfony', 'nextjs', 'next', 
                             'nuxt', 'gatsby', 'meteor', 'ember', 'backbone', 'jquery', 'bootstrap',
                             'tailwindcss', 'tailwind', 'material', 'bulma', 'foundation', 'css']
        
        db_keywords = ['postgresql', 'postgres', 'mysql', 'mongodb', 'mongo', 'redis', 'elasticsearch', 
                      'elastic', 'cassandra', 'sqlite', 'mariadb', 'couchdb', 'couch', 'neo4j', 
                      'dynamodb', 'firestore', 'fauna', 'supabase']
        
        tool_keywords = ['docker', 'kubernetes', 'k8s', 'terraform', 'ansible', 'git', 'npm', 
                        'yarn', 'pnpm', 'webpack', 'vite', 'rollup', 'parcel', 'nginx', 'apache',
                        'babel', 'eslint', 'prettier', 'jest', 'mocha', 'cypress', 'playwright']
        
        for doc in sorted(docs, key=lambda x: x.get('name', '').lower()):
            name = doc.get('name', 'Unknown')
            slug = doc.get('slug', 'unknown')
            version = doc.get('version', '')
            version_str = f" (v{version})" if version else ""
            entry = f"  • {name}{version_str} [{slug}]"
            doc_info = {'name': name, 'slug': slug, 'version': version, 'entry': entry}
            
            # Categorize based on slug or name
            slug_lower = slug.lower()
            name_lower = name.lower()
            
            # Check frameworks first (more specific matches like tailwindcss)
            if any(keyword in slug_lower or keyword in name_lower for keyword in framework_keywords):
                frameworks.append(doc_info)
            elif any(keyword in slug_lower or keyword in name_lower for keyword in db_keywords):
                databases.append(doc_info)
            elif any(keyword in slug_lower or keyword in name_lower for keyword in tool_keywords):
                tools.append(doc_info)
            elif any(keyword in slug_lower or keyword in name_lower for keyword in lang_keywords):
                languages.append(doc_info)
            else:
                other.append(doc_info)
        
        # Display categories with examples
        if languages:
            print("\n🔤 Programming Languages:", file=sys.stderr)
            for lang in languages[:5]:
                print(lang['entry'], file=sys.stderr)
            if len(languages) > 5:
                print(f"  ... and {len(languages) - 5} more", file=sys.stderr)
            
            # Show example for first language
            if languages:
                first_lang = languages[0]
                print(f"\n  Example - {first_lang['name']}:", file=sys.stderr)
                print(f"    search_docs(slug='{first_lang['slug']}', query='functions')", file=sys.stderr)
                print(f"    search_docs(slug='{first_lang['slug']}', query='classes')", file=sys.stderr)
        
        if frameworks:
            print("\n🎨 Frameworks & Libraries:", file=sys.stderr)
            for fw in frameworks[:5]:
                print(fw['entry'], file=sys.stderr)
            if len(frameworks) > 5:
                print(f"  ... and {len(frameworks) - 5} more", file=sys.stderr)
            
            # Show example for first framework
            if frameworks:
                first_fw = frameworks[0]
                print(f"\n  Example - {first_fw['name']}:", file=sys.stderr)
                print(f"    search_docs(slug='{first_fw['slug']}', query='components')", file=sys.stderr)
                print(f"    search_docs(slug='{first_fw['slug']}', query='hooks')", file=sys.stderr)
        
        if databases:
            print("\n🗄️ Databases:", file=sys.stderr)
            for db in databases[:5]:
                print(db['entry'], file=sys.stderr)
            if len(databases) > 5:
                print(f"  ... and {len(databases) - 5} more", file=sys.stderr)
            
            # Show example for first database
            if databases:
                first_db = databases[0]
                print(f"\n  Example - {first_db['name']}:", file=sys.stderr)
                print(f"    search_docs(slug='{first_db['slug']}', query='index')", file=sys.stderr)
                print(f"    search_docs(slug='{first_db['slug']}', query='query')", file=sys.stderr)
        
        if tools:
            print("\n🔧 Developer Tools:", file=sys.stderr)
            for tool in tools[:5]:
                print(tool['entry'], file=sys.stderr)
            if len(tools) > 5:
                print(f"  ... and {len(tools) - 5} more", file=sys.stderr)
            
            # Show example for first tool
            if tools:
                first_tool = tools[0]
                print(f"\n  Example - {first_tool['name']}:", file=sys.stderr)
                print(f"    search_docs(slug='{first_tool['slug']}', query='config')", file=sys.stderr)
                print(f"    search_docs(slug='{first_tool['slug']}', query='commands')", file=sys.stderr)
        
        if other:
            print("\n📦 Other Technologies:", file=sys.stderr)
            for item in other[:5]:
                print(item['entry'], file=sys.stderr)
            if len(other) > 5:
                print(f"  ... and {len(other) - 5} more", file=sys.stderr)
        
    except Exception as e:
        print(f"⚠️  Warning: Could not connect to DevDocs at {devdocs_url}", file=sys.stderr)
        print(f"   Error: {str(e)}", file=sys.stderr)
        print("", file=sys.stderr)
        print("   Please ensure DevDocs is running:", file=sys.stderr)
        print("   docker run --name devdocs -d -p 9292:9292 ghcr.io/freecodecamp/devdocs:latest", file=sys.stderr)
        print("", file=sys.stderr)
        print("   The MCP server will start but may not function properly.", file=sys.stderr)
    finally:
        await client.close()
    
    print("", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print("MCP Tools Available:", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print("", file=sys.stderr)
    
    # Tool descriptions
    tools_info = [
        {
            "name": "list_docs",
            "emoji": "📋",
            "description": "List all available documentation sets",
            "details": [
                "Returns a formatted list of all documentation sets available in DevDocs",
                "Shows name, version, and slug for each documentation set",
                "Use the slug to search within specific documentation",
                "No parameters required"
            ],
            "example": "list_docs()"
        },
        {
            "name": "search_docs",
            "emoji": "🔍",
            "description": "Search for entries within a specific documentation set",
            "details": [
                "Search for functions, classes, methods, or concepts within a specific documentation",
                "Returns up to 20 most relevant matches",
                "Results include the entry name, type, and path",
                "Use the path with get_doc_content to retrieve full documentation"
            ],
            "parameters": {
                "slug": "Documentation set identifier (e.g., 'svelte', 'python')",
                "query": "Search term to find matching entries"
            },
            "example": "search_docs(slug='react', query='useState')"
        },
        {
            "name": "get_doc_content",
            "emoji": "📄",
            "description": "Retrieve the full content of a specific documentation page",
            "details": [
                "Fetches complete documentation for a specific topic",
                "Can return either plain text or HTML format",
                "Plain text is cleaned and formatted for readability",
                "HTML preserves code examples and formatting"
            ],
            "parameters": {
                "slug": "Documentation set identifier",
                "path": "Path to the documentation page (from search results)",
                "format": "Return format - 'text' (default) or 'html'"
            },
            "example": "get_doc_content(slug='python', path='library/asyncio', format='text')"
        },
        {
            "name": "list_docset_pages",
            "emoji": "📋",
            "description": "List all pages, titles, and sections for a specific documentation set",
            "details": [
                "Shows comprehensive overview of all pages in a docset",
                "Includes page titles and section headings",
                "Provides entry names, paths, and types",
                "Useful for exploring available documentation content"
            ],
            "parameters": {
                "slug": "Documentation set identifier (e.g., 'svelte', 'tauri_v2')",
                "include_sections": "Whether to include section headings (default: true)"
            },
            "example": "list_docset_pages(slug='svelte', include_sections=true)"
        }
    ]
    
    for tool in tools_info:
        print(f"{tool['emoji']} Tool: {tool['name']}", file=sys.stderr)
        print(f"   {tool['description']}", file=sys.stderr)
        print("", file=sys.stderr)
        
        if tool['details']:
            print("   Details:", file=sys.stderr)
            for detail in tool['details']:
                print(f"   - {detail}", file=sys.stderr)
            print("", file=sys.stderr)
        
        if 'parameters' in tool:
            print("   Parameters:", file=sys.stderr)
            for param, desc in tool['parameters'].items():
                print(f"   - {param}: {desc}", file=sys.stderr)
            print("", file=sys.stderr)
        
        print(f"   Example: {tool['example']}", file=sys.stderr)
        print("-" * 40, file=sys.stderr)
    
    print("", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print("Usage Examples:", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print("", file=sys.stderr)
    
    # Generate examples based on actually available documentation
    examples = []
    
    # Try to create examples from actual available docs
    if available_docs:
        # Find some common documentation sets
        react_doc = next((d for d in available_docs if 'react' in d.get('slug', '').lower()), None)
        python_doc = next((d for d in available_docs if 'python' in d.get('slug', '').lower()), None)
        js_doc = next((d for d in available_docs if d.get('slug', '') == 'javascript'), None)
        css_doc = next((d for d in available_docs if 'css' in d.get('slug', '').lower() or 'tailwind' in d.get('slug', '').lower()), None)
        db_doc = next((d for d in available_docs if any(db in d.get('slug', '').lower() for db in ['postgresql', 'mysql', 'mongodb'])), None)
        
        if react_doc:
            examples.append((
                f"Find {react_doc.get('name', 'React')} Hooks documentation",
                f"1. list_docset_pages(slug='{react_doc.get('slug')}') # Overview of all pages\n"
                f"2. search_docs(slug='{react_doc.get('slug')}', query='hooks')\n"
                f"3. search_docs(slug='{react_doc.get('slug')}', query='useState')\n"
                f"4. get_doc_content(slug='{react_doc.get('slug')}', path='<path-from-search>')"
            ))
        
        if python_doc:
            examples.append((
                f"Learn about {python_doc.get('name', 'Python')} async/await",
                f"1. search_docs(slug='{python_doc.get('slug')}', query='async')\n"
                f"2. search_docs(slug='{python_doc.get('slug')}', query='asyncio')\n"
                f"3. get_doc_content(slug='{python_doc.get('slug')}', path='<path-from-search>')"
            ))
        
        if css_doc:
            examples.append((
                f"Explore {css_doc.get('name', 'CSS')} utilities",
                f"1. search_docs(slug='{css_doc.get('slug')}', query='flexbox')\n"
                f"2. search_docs(slug='{css_doc.get('slug')}', query='grid')\n"
                f"3. get_doc_content(slug='{css_doc.get('slug')}', path='<path-from-search>')"
            ))
        
        if db_doc:
            examples.append((
                f"Database documentation - {db_doc.get('name', 'Database')}",
                f"1. list_docs() to see all available databases\n"
                f"2. search_docs(slug='{db_doc.get('slug')}', query='index')\n"
                f"3. search_docs(slug='{db_doc.get('slug')}', query='performance')\n"
                f"4. get_doc_content(slug='{db_doc.get('slug')}', path='<path-from-search>')"
            ))
        
        # If we have at least 2 docs, show a general example
        if len(available_docs) >= 2:
            first_doc = available_docs[0]
            second_doc = available_docs[1]
            examples.append((
                "General documentation search pattern",
                f"1. list_docs() to see all {len(available_docs)} available docs\n"
                f"2. search_docs(slug='{first_doc.get('slug')}', query='getting-started')\n"
                f"3. search_docs(slug='{second_doc.get('slug')}', query='introduction')\n"
                f"4. get_doc_content(slug='<slug>', path='<path-from-search>')"
            ))
    else:
        # Fallback examples if no docs are available
        examples = [
            ("Finding documentation (when DevDocs is running)",
             "1. list_docs() to see available documentation\n"
             "2. search_docs(slug='<doc-slug>', query='<search-term>')\n"
             "3. get_doc_content(slug='<doc-slug>', path='<path>')"),
        ]
    
    for title, example in examples:
        print(f"🎯 {title}:", file=sys.stderr)
        for line in example.split('\n'):
            print(f"   {line}", file=sys.stderr)
        print("", file=sys.stderr)
    
    print("=" * 80, file=sys.stderr)
    print("✨ MCP Server Ready", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print("", file=sys.stderr)


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server
    
    # Display startup information unless --quiet flag is passed
    if "--quiet" not in sys.argv and "-q" not in sys.argv:
        await startup_info()
    elif "--help" in sys.argv or "-h" in sys.argv:
        print("DevDocs MCP Server", file=sys.stderr)
        print("", file=sys.stderr)
        print("Usage: python devdocs_mcp_server.py [options]", file=sys.stderr)
        print("", file=sys.stderr)
        print("Options:", file=sys.stderr)
        print("  --quiet, -q    Skip verbose startup information", file=sys.stderr)
        print("  --help, -h     Show this help message", file=sys.stderr)
        print("", file=sys.stderr)
        print("Environment Variables:", file=sys.stderr)
        print("  DEVDOCS_URL    URL of DevDocs instance (default: http://localhost:9292)", file=sys.stderr)
        sys.exit(0)
    else:
        print("DevDocs MCP Server starting (quiet mode)...", file=sys.stderr)
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())