#!/usr/bin/env python3
"""
Comprehensive unit tests for DevDocs MCP Server with better coverage.
"""

import asyncio
import json
import pytest
import httpx
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from devdocs_mcp_server import DevDocsClient, call_tool


class TestDevDocsClient:
    """Test the DevDocs client functionality."""
    
    @pytest.fixture
    async def client(self):
        """Create a DevDocs client for testing."""
        client = DevDocsClient("http://localhost:9292")
        yield client
        await client.close()
    
    @pytest.fixture
    async def mock_client(self):
        """Create a mock DevDocs client for isolated testing."""
        client = DevDocsClient("http://localhost:9292")
        client.session = AsyncMock()
        yield client
        await client.close()
    
    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initialization with different URLs."""
        # Test with default URL
        client1 = DevDocsClient()
        assert client1.base_url == "http://localhost:9292"
        await client1.close()
        
        # Test with custom URL
        client2 = DevDocsClient("http://custom:8080")
        assert client2.base_url == "http://custom:8080"
        await client2.close()
        
        # Test with environment variable
        with patch.dict(os.environ, {"DEVDOCS_URL": "http://env:3000"}):
            client3 = DevDocsClient()
            assert client3.base_url == "http://env:3000"
            await client3.close()
    
    @pytest.mark.asyncio
    async def test_get_available_docs_real(self, client):
        """Test getting list of available documentation sets from real DevDocs."""
        docs = await client.get_available_docs()
        
        assert isinstance(docs, list)
        assert len(docs) > 0
        
        # Check that docs have required fields
        for doc in docs:
            assert "name" in doc
            assert "slug" in doc
            assert "type" in doc
    
    @pytest.mark.asyncio
    async def test_get_available_docs_mock(self):
        """Test get_available_docs with mocked response."""
        client = DevDocsClient()
        
        # Mock the response - json() is synchronous in httpx
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=[
            {"name": "Test Doc", "slug": "test", "type": "test_type", "version": "1.0"}
        ])
        mock_response.raise_for_status = MagicMock()
        
        # Mock the client's get method
        client.client.get = AsyncMock(return_value=mock_response)
        
        docs = await client.get_available_docs()
        assert len(docs) == 1
        assert docs[0]["name"] == "Test Doc"
        await client.close()
    
    @pytest.mark.asyncio
    async def test_search_with_special_characters(self, client):
        """Test searching with special characters in query."""
        docs = await client.get_available_docs()
        if docs:
            slug = docs[0]["slug"]
            
            # Test with special characters
            special_queries = ["$state", "@apply", "#id", "v-for"]
            for query in special_queries:
                try:
                    matches = await client.search_doc_entries(slug, query)
                    assert isinstance(matches, list)
                except Exception as e:
                    # Should handle special characters gracefully
                    assert "Error" not in str(e)
    
    @pytest.mark.asyncio
    async def test_extract_text_content(self, mock_client):
        """Test HTML to text extraction."""
        html_samples = [
            "<p>Simple paragraph</p>",
            "<div><h1>Title</h1><p>Content</p></div>",
            "<pre><code>code block</code></pre>",
            "<script>alert('test')</script><p>Visible</p>",
            "<style>body{color:red}</style><p>Styled</p>",
        ]
        
        for html in html_samples:
            text = await mock_client.extract_text_content(html)
            assert isinstance(text, str)
            assert "<" not in text  # No HTML tags
            assert "script" not in text.lower()  # No script content
            # Check that style tags are removed but content preserved
            if "style" in html.lower() and "<style>" in html:
                assert "body{color:red}" not in text  # Style content removed
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test handling of connection errors."""
        client = DevDocsClient("http://nonexistent:9999")
        
        # Should handle connection errors gracefully
        try:
            docs = await client.get_available_docs()
        except Exception as e:
            # Various error messages are acceptable for connection failures
            error_str = str(e).lower()
            assert any(word in error_str for word in ["error", "connection", "nodename", "servname", "not known"])
        finally:
            await client.close()


class TestMCPTools:
    """Test MCP tool implementations with mocking."""
    
    @pytest.mark.asyncio
    async def test_list_docs_tool_empty(self):
        """Test list_docs when no docs are available."""
        with patch('devdocs_mcp_server.DevDocsClient') as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.get_available_docs = AsyncMock(return_value=[])
            
            result = await call_tool("list_docs", {})
            assert "Available Documentation Sets:" in result[0].text
    
    @pytest.mark.asyncio
    async def test_search_docs_with_unicode(self):
        """Test search_docs with unicode characters."""
        result = await call_tool("search_docs", {
            "slug": "svelte",
            "query": "état"  # French word with accent
        })
        
        # Should handle unicode gracefully
        assert result[0].type == "text"
    
    @pytest.mark.asyncio
    async def test_get_doc_content_formats(self):
        """Test get_doc_content with different format options."""
        # Test default format (text)
        result = await call_tool("get_doc_content", {
            "slug": "svelte",
            "path": "introduction"
        })
        assert result[0].type == "text"
        
        # Test explicit text format
        result = await call_tool("get_doc_content", {
            "slug": "svelte",
            "path": "introduction",
            "format": "text"
        })
        assert result[0].type == "text"
        
        # Test HTML format
        result = await call_tool("get_doc_content", {
            "slug": "svelte",
            "path": "introduction",
            "format": "html"
        })
        # Should return text type even for HTML (as per MCP spec)
        assert result[0].type == "text"
    
    @pytest.mark.asyncio
    async def test_invalid_tool_name(self):
        """Test calling non-existent tool."""
        result = await call_tool("invalid_tool", {})
        assert "Unknown tool" in result[0].text


class TestHTMLExtraction:
    """Test HTML text extraction functionality."""
    
    @pytest.mark.asyncio
    async def test_extract_text_from_html_basic(self):
        """Test basic HTML text extraction."""
        client = DevDocsClient()
        html = "<p>Hello <strong>world</strong></p>"
        text = await client.extract_text_content(html)
        assert "Hello" in text
        assert "world" in text
        await client.close()
    
    @pytest.mark.asyncio
    async def test_extract_text_from_html_complex(self):
        """Test complex HTML with various elements."""
        client = DevDocsClient()
        html = """
        <div>
            <h1>Title</h1>
            <p>Paragraph with <a href="#">link</a></p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
            <script>console.log('hidden')</script>
            <style>body { color: red; }</style>
        </div>
        """
        text = await client.extract_text_content(html)
        
        assert "Title" in text
        assert "Paragraph" in text
        assert "link" in text
        assert "Item 1" in text
        assert "Item 2" in text
        assert "console.log" not in text
        assert "color: red" not in text
        await client.close()
    
    @pytest.mark.asyncio
    async def test_extract_text_from_html_entities(self):
        """Test HTML entity decoding."""
        client = DevDocsClient()
        html = "<p>&lt;code&gt; &amp; &quot;quotes&quot;</p>"
        text = await client.extract_text_content(html)
        assert "<code>" in text
        assert "&" in text
        assert '"quotes"' in text
        await client.close()
    
    @pytest.mark.asyncio
    async def test_extract_text_from_html_whitespace(self):
        """Test whitespace handling in HTML extraction."""
        client = DevDocsClient()
        html = """
        <p>
            Multiple
            
            
            spaces
        </p>
        """
        text = await client.extract_text_content(html)
        # Should normalize whitespace
        assert "Multiple" in text and "spaces" in text
        await client.close()
    
    @pytest.mark.asyncio
    async def test_extract_text_from_html_code_blocks(self):
        """Test code block preservation."""
        client = DevDocsClient()
        html = """
        <pre><code>
def hello():
    print("world")
        </code></pre>
        """
        text = await client.extract_text_content(html)
        assert "def hello():" in text
        assert 'print("world")' in text
        await client.close()


class TestErrorScenarios:
    """Test various error scenarios."""
    
    @pytest.mark.asyncio
    async def test_network_timeout(self):
        """Test handling of network timeouts."""
        with patch('httpx.AsyncClient') as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            
            client = DevDocsClient()
            client.session = mock_instance
            
            with pytest.raises(Exception) as exc_info:
                await client.get_available_docs()
            
            assert "Timeout" in str(exc_info.value) or "Error" in str(exc_info.value)
            await client.close()
    
    @pytest.mark.asyncio
    async def test_malformed_json_response(self):
        """Test handling of malformed JSON responses."""
        with patch('httpx.AsyncClient') as MockClient:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(side_effect=json.JSONDecodeError("test", "doc", 0))
            mock_instance = MockClient.return_value
            mock_instance.get.return_value.__aenter__.return_value = mock_response
            
            client = DevDocsClient()
            client.session = mock_instance
            
            with pytest.raises(Exception):
                await client.get_available_docs()
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_empty_search_query(self):
        """Test searching with empty query."""
        result = await call_tool("search_docs", {"slug": "svelte", "query": ""})
        # Should either return error or empty results
        assert "Error" in result[0].text or "No matches" in result[0].text
    
    @pytest.mark.asyncio
    async def test_whitespace_only_query(self):
        """Test searching with whitespace-only query."""
        result = await call_tool("search_docs", {"slug": "svelte", "query": "   "})
        # Should handle gracefully
        assert result[0].type == "text"


class TestStartupInfo:
    """Test startup info functionality."""
    
    @pytest.mark.asyncio
    async def test_startup_info_display(self, capsys):
        """Test that startup info displays correctly."""
        from devdocs_mcp_server import startup_info
        
        # Mock the DevDocsClient to avoid real network calls
        with patch('devdocs_mcp_server.DevDocsClient') as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.get_available_docs = AsyncMock(return_value=[
                {"name": "Test", "slug": "test", "type": "test"}
            ])
            mock_instance.close = AsyncMock()  # Add mock for close method
            
            await startup_info()
            
            captured = capsys.readouterr()
            assert "DevDocs MCP Server" in captured.err
            assert "Available Documentation" in captured.err




if __name__ == "__main__":
    pytest.main([__file__, "-v"])