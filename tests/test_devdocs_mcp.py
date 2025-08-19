#!/usr/bin/env python3
"""
Unit tests for DevDocs MCP Server

Tests all MCP server endpoints against a running DevDocs instance.
Assumes DevDocs is running on localhost:9292 with Svelte and TailwindCSS loaded.
"""

import asyncio
import json
import pytest
import httpx
import sys
import os
from unittest.mock import AsyncMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from devdocs_mcp_server import DevDocsClient, call_tool


class TestDevDocsClient:
    """Test the DevDocs client functionality."""
    
    @pytest.fixture
    async def client(self):
        """Create a DevDocs client for testing."""
        # Create a fresh client for each test
        from devdocs_mcp_server import DevDocsClient
        client = DevDocsClient("http://localhost:9292")
        yield client
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_available_docs(self, client):
        """Test getting list of available documentation sets."""
        docs = await client.get_available_docs()
        
        assert isinstance(docs, list)
        assert len(docs) > 0
        
        # Check that docs have required fields
        for doc in docs:
            assert "name" in doc
            assert "slug" in doc
            assert "type" in doc
        
        # Check for Svelte and TailwindCSS
        doc_slugs = [doc["slug"] for doc in docs]
        assert any("svelte" in slug for slug in doc_slugs), "Svelte documentation should be available"
        assert any("tailwind" in slug for slug in doc_slugs), "TailwindCSS documentation should be available"
    
    @pytest.mark.asyncio
    async def test_get_doc_index_svelte(self, client):
        """Test getting index for Svelte documentation."""
        # Find Svelte slug
        docs = await client.get_available_docs()
        svelte_slug = None
        for doc in docs:
            if "svelte" in doc["slug"]:
                svelte_slug = doc["slug"]
                break
        
        assert svelte_slug is not None, "Svelte documentation not found"
        
        index = await client.get_doc_index(svelte_slug)
        assert "entries" in index
        assert "types" in index
        assert len(index["entries"]) > 0
        
        # Check entry structure
        first_entry = index["entries"][0]
        assert "name" in first_entry
        assert "path" in first_entry
    
    @pytest.mark.asyncio
    async def test_get_doc_index_tailwindcss(self, client):
        """Test getting index for TailwindCSS documentation."""
        # Find TailwindCSS slug
        docs = await client.get_available_docs()
        tailwind_slug = None
        for doc in docs:
            if "tailwind" in doc["slug"]:
                tailwind_slug = doc["slug"]
                break
        
        assert tailwind_slug is not None, "TailwindCSS documentation not found"
        
        index = await client.get_doc_index(tailwind_slug)
        assert "entries" in index
        assert "types" in index
        assert len(index["entries"]) > 0
    
    @pytest.mark.asyncio
    async def test_search_doc_entries_svelte(self, client):
        """Test searching entries in Svelte documentation."""
        docs = await client.get_available_docs()
        svelte_slug = next((doc["slug"] for doc in docs if "svelte" in doc["slug"]), None)
        assert svelte_slug is not None
        
        # Test search for "component"
        matches = await client.search_doc_entries(svelte_slug, "component")
        assert isinstance(matches, list)
        
        if matches:
            # Verify match structure
            for match in matches:
                assert "name" in match
                assert "path" in match
                assert "component" in match["name"].lower()
    
    @pytest.mark.asyncio
    async def test_search_doc_entries_tailwindcss(self, client):
        """Test searching entries in TailwindCSS documentation."""
        docs = await client.get_available_docs()
        tailwind_slug = next((doc["slug"] for doc in docs if "tailwind" in doc["slug"]), None)
        assert tailwind_slug is not None
        
        # Test search for "color"
        matches = await client.search_doc_entries(tailwind_slug, "color")
        assert isinstance(matches, list)
        
        if matches:
            # Verify match structure
            for match in matches:
                assert "name" in match
                assert "path" in match
                assert "color" in match["name"].lower()
    
    @pytest.mark.asyncio
    async def test_get_doc_content(self, client):
        """Test getting content from a documentation page."""
        docs = await client.get_available_docs()
        svelte_slug = next((doc["slug"] for doc in docs if "svelte" in doc["slug"]), None)
        assert svelte_slug is not None
        
        # Get first entry to test content retrieval
        index = await client.get_doc_index(svelte_slug)
        first_entry = index["entries"][0]
        path = first_entry["path"]
        
        html_content = await client.get_doc_content(svelte_slug, path)
        assert isinstance(html_content, str)
        assert len(html_content) > 0
        
        # Test text extraction
        text_content = await client.extract_text_content(html_content)
        assert isinstance(text_content, str)
        assert len(text_content) > 0
        assert len(text_content) < len(html_content)  # Should be shorter than HTML


class TestMCPServerTools:
    """Test the MCP server tool implementations."""
    
    @pytest.mark.asyncio
    async def test_list_docs_tool(self):
        """Test the list_docs MCP tool."""
        result = await call_tool("list_docs", {})
        
        assert len(result) == 1
        assert result[0].type == "text"
        content = result[0].text
        
        assert "Available Documentation Sets:" in content
        assert "svelte" in content.lower()
        assert "tailwind" in content.lower()
    
    @pytest.mark.asyncio
    async def test_search_docs_tool_svelte(self):
        """Test the search_docs MCP tool with Svelte."""
        # Find Svelte slug first
        docs_result = await call_tool("list_docs", {})
        docs_content = docs_result[0].text
        
        # Extract Svelte slug from the list
        svelte_slug = None
        for line in docs_content.split('\n'):
            if 'svelte' in line.lower() and 'slug:' in line:
                svelte_slug = line.split('slug: `')[1].split('`')[0]
                break
        
        assert svelte_slug is not None, "Could not find Svelte slug"
        
        result = await call_tool("search_docs", {"slug": svelte_slug, "query": "component"})
        
        assert len(result) == 1
        assert result[0].type == "text"
        content = result[0].text
        
        assert f"Search results for 'component' in {svelte_slug}:" in content
    
    @pytest.mark.asyncio
    async def test_search_docs_tool_tailwindcss(self):
        """Test the search_docs MCP tool with TailwindCSS."""
        # Find TailwindCSS slug first
        docs_result = await call_tool("list_docs", {})
        docs_content = docs_result[0].text
        
        # Extract TailwindCSS slug from the list
        tailwind_slug = None
        for line in docs_content.split('\n'):
            if 'tailwind' in line.lower() and 'slug:' in line:
                tailwind_slug = line.split('slug: `')[1].split('`')[0]
                break
        
        assert tailwind_slug is not None, "Could not find TailwindCSS slug"
        
        result = await call_tool("search_docs", {"slug": tailwind_slug, "query": "color"})
        
        assert len(result) == 1
        assert result[0].type == "text"
        content = result[0].text
        
        assert f"Search results for 'color' in {tailwind_slug}:" in content
    
    @pytest.mark.asyncio
    async def test_get_doc_content_tool(self):
        """Test the get_doc_content MCP tool."""
        # Get available docs and find Svelte
        docs_result = await call_tool("list_docs", {})
        docs_content = docs_result[0].text
        
        svelte_slug = None
        for line in docs_content.split('\n'):
            if 'svelte' in line.lower() and 'slug:' in line:
                svelte_slug = line.split('slug: `')[1].split('`')[0]
                break
        
        assert svelte_slug is not None
        
        # Search for an entry to get a valid path
        search_result = await call_tool("search_docs", {"slug": svelte_slug, "query": "introduction"})
        search_content = search_result[0].text
        
        # Extract a path from search results
        test_path = None
        for line in search_content.split('\n'):
            if 'path: `' in line:
                test_path = line.split('path: `')[1].split('`')[0]
                break
        
        if test_path:
            # Test getting content in text format
            result = await call_tool("get_doc_content", {
                "slug": svelte_slug, 
                "path": test_path, 
                "format": "text"
            })
            
            assert len(result) == 1
            assert result[0].type == "text"
            content = result[0].text
            assert len(content) > 0
            
            # Test getting content in HTML format
            html_result = await call_tool("get_doc_content", {
                "slug": svelte_slug, 
                "path": test_path, 
                "format": "html"
            })
            
            assert len(html_result) == 1
            html_content = html_result[0].text
            assert "<" in html_content  # Should contain HTML tags
    
    @pytest.mark.asyncio
    async def test_search_docs_tool_error_handling(self):
        """Test error handling in search_docs tool."""
        # Test missing parameters
        result = await call_tool("search_docs", {"slug": "svelte"})
        assert "Error: Both 'slug' and 'query' are required" in result[0].text
        
        # Test invalid slug
        result = await call_tool("search_docs", {"slug": "nonexistent", "query": "test"})
        assert "Error searching nonexistent:" in result[0].text
    
    @pytest.mark.asyncio
    async def test_get_doc_content_tool_error_handling(self):
        """Test error handling in get_doc_content tool."""
        # Test missing parameters
        result = await call_tool("get_doc_content", {"slug": "svelte"})
        assert "Error: Both 'slug' and 'path' are required" in result[0].text
        
        # Test invalid path - DevDocs returns a JavaScript requirement page for invalid paths
        result = await call_tool("get_doc_content", {"slug": "svelte", "path": "nonexistent"})
        # Either get an error or the JavaScript requirement message
        assert ("Error getting content" in result[0].text or "DevDocs requires JavaScript" in result[0].text)


class TestIntegration:
    """Integration tests that verify end-to-end functionality."""
    
    @pytest.mark.asyncio
    async def test_full_workflow_svelte(self):
        """Test complete workflow: list -> search -> get content for Svelte."""
        # Step 1: List docs
        docs_result = await call_tool("list_docs", {})
        assert "svelte" in docs_result[0].text.lower()
        
        # Extract Svelte slug
        svelte_slug = None
        for line in docs_result[0].text.split('\n'):
            if 'svelte' in line.lower() and 'slug:' in line:
                svelte_slug = line.split('slug: `')[1].split('`')[0]
                break
        
        assert svelte_slug is not None
        
        # Step 2: Search for entries
        search_result = await call_tool("search_docs", {
            "slug": svelte_slug, 
            "query": "bind"
        })
        
        search_content = search_result[0].text
        assert "Search results for 'bind'" in search_content
        
        # Step 3: Get content for first match (if any)
        if "path: `" in search_content:
            test_path = search_content.split('path: `')[1].split('`')[0]
            
            content_result = await call_tool("get_doc_content", {
                "slug": svelte_slug,
                "path": test_path,
                "format": "text"
            })
            
            assert len(content_result[0].text) > 0
    
    @pytest.mark.asyncio
    async def test_full_workflow_tailwindcss(self):
        """Test complete workflow: list -> search -> get content for TailwindCSS."""
        # Step 1: List docs
        docs_result = await call_tool("list_docs", {})
        assert "tailwind" in docs_result[0].text.lower()
        
        # Extract TailwindCSS slug
        tailwind_slug = None
        for line in docs_result[0].text.split('\n'):
            if 'tailwind' in line.lower() and 'slug:' in line:
                tailwind_slug = line.split('slug: `')[1].split('`')[0]
                break
        
        assert tailwind_slug is not None
        
        # Step 2: Search for entries
        search_result = await call_tool("search_docs", {
            "slug": tailwind_slug, 
            "query": "color"
        })
        
        search_content = search_result[0].text
        assert "Search results for 'color'" in search_content
        
        # Step 3: Get content for first match (if any)
        if "path: `" in search_content:
            test_path = search_content.split('path: `')[1].split('`')[0]
            
            content_result = await call_tool("get_doc_content", {
                "slug": tailwind_slug,
                "path": test_path,
                "format": "text"
            })
            
            assert len(content_result[0].text) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])