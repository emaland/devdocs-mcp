#!/usr/bin/env python3
"""
Simple test runner that exercises MCP endpoints without pytest.
Runs against DevDocs on localhost:9292 with Svelte and TailwindCSS loaded.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from devdocs_mcp_server import call_tool


async def test_list_docs():
    """Test listing all documentation sets."""
    print("Testing list_docs...")
    result = await call_tool("list_docs", {})
    content = result[0].text
    
    assert "Available Documentation Sets:" in content
    assert "svelte" in content.lower()
    assert "tailwind" in content.lower()
    
    print("✓ list_docs passed")
    return content


async def test_search_docs():
    """Test searching documentation entries."""
    print("\nTesting search_docs...")
    
    # Test Svelte search
    result = await call_tool("search_docs", {"slug": "svelte", "query": "component"})
    content = result[0].text
    
    print(f"Svelte search result:\n{content}")
    assert "Search results for 'component' in svelte:" in content
    
    # Test TailwindCSS search
    result = await call_tool("search_docs", {"slug": "tailwindcss", "query": "color"})
    content = result[0].text
    
    print(f"\nTailwindCSS search result:\n{content}")
    assert "Search results for 'color' in tailwindcss:" in content
    
    print("✓ search_docs passed")
    return content


async def test_get_doc_content():
    """Test getting documentation content."""
    print("\nTesting get_doc_content...")
    
    # First search for an entry to get a valid path
    search_result = await call_tool("search_docs", {"slug": "svelte", "query": "introduction"})
    search_content = search_result[0].text
    
    # Extract a path from search results
    test_path = None
    for line in search_content.split('\n'):
        if 'path: `' in line:
            test_path = line.split('path: `')[1].split('`')[0]
            break
    
    if test_path:
        # Test text format
        result = await call_tool("get_doc_content", {
            "slug": "svelte", 
            "path": test_path, 
            "format": "text"
        })
        
        text_content = result[0].text
        print(f"Retrieved text content ({len(text_content)} chars)")
        print(f"Preview: {text_content[:200]}...")
        
        # Test HTML format
        html_result = await call_tool("get_doc_content", {
            "slug": "svelte", 
            "path": test_path, 
            "format": "html"
        })
        
        html_content = html_result[0].text
        print(f"Retrieved HTML content ({len(html_content)} chars)")
        assert "<" in html_content
        
        print("✓ get_doc_content passed")
    else:
        print("⚠ No valid path found for content test")


async def test_error_handling():
    """Test error handling in MCP tools."""
    print("\nTesting error handling...")
    
    # Test missing parameters
    result = await call_tool("search_docs", {"slug": "svelte"})
    assert "Error: Both 'slug' and 'query' are required" in result[0].text
    
    # Test invalid slug
    result = await call_tool("search_docs", {"slug": "nonexistent", "query": "test"})
    assert "Error searching nonexistent:" in result[0].text
    
    print("✓ Error handling passed")


async def main():
    """Run all tests."""
    print("DevDocs MCP Server Test Suite")
    print("=" * 40)
    print("Testing against DevDocs on localhost:9292")
    print("Expecting Svelte and TailwindCSS to be available")
    print()
    
    try:
        await test_list_docs()
        await test_search_docs()
        await test_get_doc_content()
        await test_error_handling()
        
        print("\n" + "=" * 40)
        print("✓ All tests passed!")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        print("\nMake sure DevDocs is running:")
        print("docker run --name devdocs -d -p 9292:9292 ghcr.io/freecodecamp/devdocs:latest")
        sys.exit(1)
    
    finally:
        # Client cleanup handled by MCP server
        pass


if __name__ == "__main__":
    asyncio.run(main())