#!/usr/bin/env python3
"""
AutoDoc CLI - Main entry point for the documentation system
"""

import click
import sys
from pathlib import Path
from colorama import init, Fore, Style

# Add autodoc to path if needed
sys.path.insert(0, str(Path(__file__).parent.parent))

from autodoc.config import AutoDocConfig
from autodoc.core import DocumentationSystem
from autodoc.utils import detect_project_directories, analyze_project_structure

# Initialize colorama
init()

@click.group()
@click.version_option(version='1.0.0')
def cli():
    """AutoDoc - Intelligent Documentation System
    
    Prevents code redundancy through semantic search and documentation.
    """
    pass

@cli.command()
@click.option('--config', default='autodoc.config.json', help='Config file path')
@click.option('--project-root', default='.', help='Project root directory')
@click.option('--docs-dir', default='autodoc_docs', help='Documentation directory')
@click.option('--llm-model', default='codellama:7b', help='LLM model for analysis')
@click.option('--port', default=3015, help='MCP server port (3010-3020 recommended)')
def init(config, project_root, docs_dir, llm_model, port):
    """Initialize AutoDoc in current project"""
    
    print(f"\n{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🚀 Initializing AutoDoc{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}\n")
    
    # Detect project structure
    print(f"{Fore.YELLOW}🔍 Analyzing project structure...{Style.RESET_ALL}")
    detected_dirs = detect_project_directories(project_root)
    project_analysis = analyze_project_structure(project_root)
    
    print(f"  Framework: {Fore.GREEN}{project_analysis['framework']}{Style.RESET_ALL}")
    print(f"  Python files: {Fore.GREEN}{project_analysis['total_python_files']}{Style.RESET_ALL}")
    print(f"  Detected directories: {Fore.GREEN}{', '.join(detected_dirs)}{Style.RESET_ALL}")
    
    # Create config with detected directories
    autodoc_config = AutoDocConfig(
        project_root=project_root,
        docs_dir=docs_dir,
        llm_model=llm_model,
        mcp_server_port=port,
        watch_directories=detected_dirs if detected_dirs else ['.']
    )
    
    # Create directories
    paths = autodoc_config.get_absolute_paths()
    for name, path in paths.items():
        if name != 'project_root':
            path.mkdir(parents=True, exist_ok=True)
            print(f"{Fore.GREEN}✅ Created: {path}{Style.RESET_ALL}")
    
    # Save config
    autodoc_config.to_file(config)
    print(f"{Fore.GREEN}✅ Config saved: {config}{Style.RESET_ALL}")
    
    # Create .gitignore entries
    gitignore_entries = [
        f"\n# AutoDoc",
        f"{docs_dir}/",
        f"{autodoc_config.vector_db_dir}/",
        "autodoc.config.json"
    ]
    
    gitignore_path = Path(project_root) / '.gitignore'
    if gitignore_path.exists():
        with open(gitignore_path, 'a') as f:
            f.write('\n'.join(gitignore_entries))
        print(f"{Fore.GREEN}✅ Updated .gitignore{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}AutoDoc initialized successfully!{Style.RESET_ALL}")
    print(f"Next steps:")
    print(f"  1. Run initial scan: {Fore.YELLOW}autodoc scan{Style.RESET_ALL}")
    print(f"  2. Start MCP server: {Fore.YELLOW}autodoc server{Style.RESET_ALL}")
    print(f"  3. Start file watcher: {Fore.YELLOW}autodoc watch{Style.RESET_ALL}")

@cli.command()
@click.option('--config', default='autodoc.config.json', help='Config file path')
@click.option('--directories', '-d', multiple=True, help='Directories to scan')
@click.option('--parallel/--sequential', default=True, help='Parallel processing')
def scan(config, directories, parallel):
    """Scan project and generate documentation"""
    
    print(f"\n{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}📊 Scanning Project{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}\n")
    
    # Load config
    autodoc_config = AutoDocConfig.from_file(config)
    
    # Use provided directories or config defaults
    scan_dirs = list(directories) if directories else autodoc_config.watch_directories
    
    # Initialize documentation system with all config
    doc_system = DocumentationSystem(
        project_root=autodoc_config.project_root,
        docs_dir=autodoc_config.docs_dir,
        llm_model=autodoc_config.llm_model,
        embedding_model=autodoc_config.embedding_model,
        vector_db_dir=autodoc_config.vector_db_dir
    )
    
    # Process project
    doc_system.process_project(scan_dirs, parallel=parallel)
    
    print(f"\n{Fore.GREEN}✅ Scan complete!{Style.RESET_ALL}")
    print(f"Documentation available in: {autodoc_config.docs_dir}/")

@cli.command()
@click.option('--config', default='autodoc.config.json', help='Config file path')
@click.option('--directories', '-d', multiple=True, help='Directories to watch')
@click.option('--scan-first/--no-scan', default=False, help='Scan before watching')
def watch(config, directories, scan_first):
    """Watch files and update documentation automatically"""
    
    print(f"\n{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}👁️ Starting File Watcher{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}\n")
    
    # Load config
    autodoc_config = AutoDocConfig.from_file(config)
    watch_dirs = list(directories) if directories else autodoc_config.watch_directories
    
    # Initialize documentation system with all config
    doc_system = DocumentationSystem(
        project_root=autodoc_config.project_root,
        docs_dir=autodoc_config.docs_dir,
        llm_model=autodoc_config.llm_model,
        embedding_model=autodoc_config.embedding_model,
        vector_db_dir=autodoc_config.vector_db_dir
    )
    
    # Scan first if requested
    if scan_first:
        print(f"{Fore.YELLOW}Running initial scan...{Style.RESET_ALL}")
        doc_system.process_project(watch_dirs, parallel=True)
    
    # Start watcher
    doc_system.start_file_watcher(watch_dirs)

@cli.command()
@click.option('--config', default='autodoc.config.json', help='Config file path')
@click.option('--port', type=int, help='Server port (overrides config)')
def server(config, port):
    """Start MCP server for Claude integration"""
    
    print(f"\n{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🚀 Starting MCP Server{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}\n")
    
    # Load config
    autodoc_config = AutoDocConfig.from_file(config)
    
    # Use provided port or config port
    server_port = port if port else autodoc_config.mcp_server_port
    
    # Set environment variables for MCP server
    import os
    os.environ['DOC_SYSTEM_PROJECT_ROOT'] = autodoc_config.project_root
    os.environ['DOC_SYSTEM_DOCS_DIR'] = autodoc_config.docs_dir
    
    # Start MCP server
    import subprocess
    import sys
    
    server_path = Path(__file__).parent / 'mcp_server' / 'server.py'
    
    print(f"{Fore.CYAN}Server starting on port {server_port}...{Style.RESET_ALL}")
    print(f"Connect Claude to: localhost:{server_port}")
    print(f"Press {Fore.YELLOW}Ctrl+C{Style.RESET_ALL} to stop\n")
    
    try:
        subprocess.run([sys.executable, str(server_path)])
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Server stopped.{Style.RESET_ALL}")

@cli.command()
@click.argument('query')
@click.option('--config', default='autodoc.config.json', help='Config file path')
@click.option('--limit', default=10, help='Number of results')
def search(query, config, limit):
    """Search documentation (useful for testing)"""
    
    # Load config
    autodoc_config = AutoDocConfig.from_file(config)
    
    # Initialize documentation system
    from autodoc.core import DocumentationSystem
    doc_system = DocumentationSystem(
        project_root=autodoc_config.project_root,
        docs_dir=autodoc_config.docs_dir
    )
    
    # Search
    results = doc_system.indexer.search(query, limit=limit)
    
    print(f"\n{Fore.CYAN}Search Results for '{query}':{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
    
    for i, result in enumerate(results, 1):
        meta = result.get('metadata', {})
        print(f"\n{i}. {Fore.GREEN}{meta.get('name', 'Unknown')}{Style.RESET_ALL}")
        print(f"   Type: {meta.get('type', 'unknown')}")
        print(f"   File: {meta.get('file_path', 'unknown')}")
        print(f"   Line: {meta.get('line_number', 0)}")
        print(f"   Relevance: {1.0 - result.get('distance', 1.0):.2f}")

@cli.command()
def info():
    """Show AutoDoc system information"""
    
    print(f"\n{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}AutoDoc System Information{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}\n")
    
    print(f"Version: 1.0.0")
    print(f"Python: {sys.version.split()[0]}")
    
    # Check for optional dependencies
    print(f"\n{Fore.YELLOW}Dependencies:{Style.RESET_ALL}")
    
    deps = {
        'chromadb': 'Vector Database',
        'ollama': 'LLM Integration',
        'sentence_transformers': 'Embeddings',
        'watchdog': 'File Watching',
        'mcp': 'MCP Server'
    }
    
    for module, description in deps.items():
        try:
            __import__(module)
            print(f"  ✅ {description} ({module})")
        except ImportError:
            print(f"  ❌ {description} ({module})")
    
    # Check for Ollama
    print(f"\n{Fore.YELLOW}Ollama Status:{Style.RESET_ALL}")
    try:
        import subprocess
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✅ Ollama installed")
            if 'codellama' in result.stdout:
                print(f"  ✅ CodeLlama model available")
            else:
                print(f"  ⚠️ CodeLlama model not found")
        else:
            print(f"  ❌ Ollama not responding")
    except FileNotFoundError:
        print(f"  ❌ Ollama not installed")

if __name__ == '__main__':
    cli()