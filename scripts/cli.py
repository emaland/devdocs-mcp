#!/usr/bin/env python3
"""
CLI tool for testing DevDocs MCP Server endpoints

Usage:
    python scripts/cli.py list
    python scripts/cli.py search svelte component
    python scripts/cli.py get svelte introduction
    python scripts/cli.py interactive
"""

import asyncio
import argparse
import json
import sys
import os
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from devdocs_mcp_server import DevDocsClient


class DevDocsCLI:
    """CLI interface for DevDocs MCP Server."""
    
    def __init__(self, base_url: Optional[str] = None):
        self.client = DevDocsClient(base_url)
        self.docs_cache = None
    
    async def list_docs(self, format_output: str = "table"):
        """List all available documentation sets."""
        try:
            docs = await self.client.get_available_docs()
            self.docs_cache = docs
            
            if format_output == "json":
                print(json.dumps(docs, indent=2))
            elif format_output == "simple":
                for doc in docs:
                    slug = doc.get('slug', 'unknown')
                    print(slug)
            else:  # table format
                print("\n📚 Available Documentation Sets:\n")
                print(f"{'Name':<30} {'Slug':<25} {'Version':<10}")
                print("=" * 70)
                
                for doc in docs:
                    name = doc.get('name', 'Unknown')[:29]
                    slug = doc.get('slug', 'unknown')[:24]
                    version = doc.get('version', '')[:9]
                    print(f"{name:<30} {slug:<25} {version:<10}")
                
                print(f"\nTotal: {len(docs)} documentation sets available")
                
        except Exception as e:
            print(f"❌ Error listing docs: {e}", file=sys.stderr)
            return 1
        return 0
    
    async def search_docs(self, slug: str, query: str, limit: int = 10):
        """Search for entries in a documentation set."""
        try:
            matches = await self.client.search_doc_entries(slug, query)
            
            if not matches:
                print(f"No matches found for '{query}' in {slug}")
                return 0
            
            print(f"\n🔍 Search results for '{query}' in {slug}:\n")
            
            for i, entry in enumerate(matches[:limit], 1):
                name = entry.get('name', 'Unknown')
                path = entry.get('path', '')
                entry_type = entry.get('type', '')
                
                type_str = f" [{entry_type}]" if entry_type else ""
                print(f"{i:2}. {name}{type_str}")
                print(f"    Path: {path}")
                print()
            
            if len(matches) > limit:
                print(f"... and {len(matches) - limit} more results")
                
        except Exception as e:
            print(f"❌ Error searching {slug}: {e}", file=sys.stderr)
            return 1
        return 0
    
    async def get_content(self, slug: str, path: str, format_type: str = "text"):
        """Get content from a documentation page."""
        try:
            if format_type == "html":
                content = await self.client.get_doc_content(slug, path)
            else:
                html_content = await self.client.get_doc_content(slug, path)
                content = await self.client.extract_text_content(html_content)
            
            print(f"\n📄 Content from {slug}/{path}:\n")
            print("=" * 70)
            
            if format_type == "text" and len(content) > 2000:
                # Show preview for long content
                print(content[:2000])
                print(f"\n... (truncated, {len(content)} total characters)")
                print("\nUse --format html to see full HTML content")
            else:
                print(content)
                
        except Exception as e:
            print(f"❌ Error getting content: {e}", file=sys.stderr)
            return 1
        return 0
    
    async def interactive_mode(self):
        """Interactive mode for exploring documentation."""
        print("🚀 DevDocs Interactive Mode")
        print("Commands: list, search <slug> <query>, get <slug> <path>, help, quit")
        print("-" * 50)
        
        while True:
            try:
                cmd = input("\ndevdocs> ").strip()
                
                if not cmd:
                    continue
                
                parts = cmd.split()
                command = parts[0].lower()
                
                if command in ('quit', 'exit', 'q'):
                    print("Goodbye!")
                    break
                
                elif command == 'help':
                    print("\nAvailable commands:")
                    print("  list                    - List all documentation sets")
                    print("  search <slug> <query>   - Search in a documentation set")
                    print("  get <slug> <path>       - Get content from a page")
                    print("  slugs                   - Show just the slugs (for easy copying)")
                    print("  help                    - Show this help")
                    print("  quit                    - Exit interactive mode")
                
                elif command == 'list':
                    await self.list_docs()
                
                elif command == 'slugs':
                    await self.list_docs(format_output="simple")
                
                elif command == 'search':
                    if len(parts) < 3:
                        print("Usage: search <slug> <query>")
                        continue
                    slug = parts[1]
                    query = ' '.join(parts[2:])
                    await self.search_docs(slug, query)
                
                elif command == 'get':
                    if len(parts) < 3:
                        print("Usage: get <slug> <path>")
                        continue
                    slug = parts[1]
                    path = ' '.join(parts[2:])
                    await self.get_content(slug, path)
                
                else:
                    print(f"Unknown command: {command}")
                    print("Type 'help' for available commands")
                    
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
                continue
            except Exception as e:
                print(f"Error: {e}")
                continue
    
    async def close(self):
        """Clean up resources."""
        await self.client.close()


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DevDocs MCP Server CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                          List all documentation sets
  %(prog)s list --format json            List in JSON format
  %(prog)s search svelte component       Search for 'component' in Svelte docs
  %(prog)s get svelte introduction       Get content from Svelte introduction
  %(prog)s get svelte introduction --format html  Get HTML content
  %(prog)s interactive                   Start interactive mode
"""
    )
    
    parser.add_argument(
        '--url',
        default="http://localhost:9292",
        help='DevDocs server URL (default: http://localhost:9292)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all documentation sets')
    list_parser.add_argument(
        '--format',
        choices=['table', 'json', 'simple'],
        default='table',
        help='Output format'
    )
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search documentation')
    search_parser.add_argument('slug', help='Documentation slug (e.g., svelte, tailwindcss)')
    search_parser.add_argument('query', nargs='+', help='Search query')
    search_parser.add_argument('--limit', type=int, default=10, help='Max results to show')
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Get documentation content')
    get_parser.add_argument('slug', help='Documentation slug')
    get_parser.add_argument('path', nargs='+', help='Page path')
    get_parser.add_argument(
        '--format',
        choices=['text', 'html'],
        default='text',
        help='Content format'
    )
    
    # Interactive mode
    interactive_parser = subparsers.add_parser('interactive', help='Interactive mode')
    
    args = parser.parse_args()
    
    # Initialize CLI
    cli = DevDocsCLI(args.url)
    
    try:
        if args.command == 'list':
            return await cli.list_docs(args.format)
        
        elif args.command == 'search':
            query = ' '.join(args.query)
            return await cli.search_docs(args.slug, query, args.limit)
        
        elif args.command == 'get':
            path = ' '.join(args.path)
            return await cli.get_content(args.slug, path, args.format)
        
        elif args.command == 'interactive':
            await cli.interactive_mode()
            return 0
        
        else:
            parser.print_help()
            return 1
            
    except KeyboardInterrupt:
        print("\nInterrupted")
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        await cli.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))