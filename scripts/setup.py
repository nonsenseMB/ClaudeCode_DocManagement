#!/usr/bin/env python3
"""
Setup script for Intelligent Documentation System
Initializes the project structure and performs initial analysis
"""

import os
import sys
import subprocess
from pathlib import Path
import click
from colorama import init, Fore, Style

# Initialize colorama
init()

def print_header():
    """Print setup header"""
    print(f"\n{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🚀 Intelligent Documentation System Setup{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}\n")

def check_python_version():
    """Check if Python version is 3.8+"""
    if sys.version_info < (3, 8):
        print(f"{Fore.RED}❌ Python 3.8+ required. Current: {sys.version}{Style.RESET_ALL}")
        sys.exit(1)
    print(f"{Fore.GREEN}✅ Python {sys.version.split()[0]} detected{Style.RESET_ALL}")

def install_dependencies():
    """Install required Python packages"""
    print(f"\n{Fore.YELLOW}📦 Installing dependencies...{Style.RESET_ALL}")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True)
        print(f"{Fore.GREEN}✅ Dependencies installed successfully{Style.RESET_ALL}")
    except subprocess.CalledProcessError as e:
        print(f"{Fore.RED}❌ Failed to install dependencies: {e}{Style.RESET_ALL}")
        sys.exit(1)

def setup_ollama():
    """Check and setup Ollama (optional)"""
    print(f"\n{Fore.YELLOW}🤖 Checking Ollama setup...{Style.RESET_ALL}")
    
    try:
        # Check if ollama is installed
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"{Fore.GREEN}✅ Ollama detected{Style.RESET_ALL}")
            
            # Check for codellama model
            if "codellama" not in result.stdout:
                print(f"{Fore.YELLOW}📥 Pulling codellama:7b model...{Style.RESET_ALL}")
                try:
                    subprocess.run(["ollama", "pull", "codellama:7b"], check=True)
                    print(f"{Fore.GREEN}✅ CodeLlama model installed{Style.RESET_ALL}")
                except:
                    print(f"{Fore.YELLOW}⚠️ Could not pull CodeLlama model. LLM features will be limited.{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}✅ CodeLlama model available{Style.RESET_ALL}")
        else:
            raise Exception("Ollama not found")
            
    except (FileNotFoundError, Exception):
        print(f"{Fore.YELLOW}⚠️ Ollama not found. Install from https://ollama.ai for enhanced analysis.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}   The system will work without it but with limited features.{Style.RESET_ALL}")

def create_directories():
    """Create necessary project directories"""
    print(f"\n{Fore.YELLOW}📁 Creating project structure...{Style.RESET_ALL}")
    
    directories = [
        "scripts",
        "mcp_server", 
        "docs/files",
        "docs/generated",
        "vector_db"
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    print(f"{Fore.GREEN}✅ Directory structure created{Style.RESET_ALL}")

def create_env_file():
    """Create .env file with default configuration"""
    env_path = Path(".env")
    
    if not env_path.exists():
        print(f"\n{Fore.YELLOW}⚙️ Creating .env configuration...{Style.RESET_ALL}")
        
        env_content = """# Intelligent Documentation System Configuration

# LLM Model (options: codellama:7b, codellama:13b, none)
DOC_SYSTEM_LLM_MODEL=codellama:7b

# Paths
DOC_SYSTEM_PROJECT_ROOT=.
DOC_SYSTEM_DOCS_DIR=docs
DOC_SYSTEM_DB_PATH=./vector_db

# MCP Server
MCP_SERVER_PORT=3000

# File Watcher
WATCH_DIRECTORIES=src,app,scripts
WATCH_ENABLED=false

# Processing
PARALLEL_PROCESSING=true
MAX_WORKERS=4
"""
        
        with open(env_path, 'w') as f:
            f.write(env_content)
        
        print(f"{Fore.GREEN}✅ .env file created{Style.RESET_ALL}")
    else:
        print(f"{Fore.CYAN}ℹ️ .env file already exists{Style.RESET_ALL}")

def create_mcp_config():
    """Create MCP server configuration"""
    print(f"\n{Fore.YELLOW}🔧 Creating MCP configuration...{Style.RESET_ALL}")
    
    config_path = Path("mcp_config.json")
    
    config = {
        "name": "documentation-system",
        "description": "Intelligent Documentation System MCP Server",
        "version": "1.0.0",
        "server": {
            "command": ["python", "mcp_server/server.py"],
            "env": {
                "DOC_SYSTEM_PROJECT_ROOT": ".",
                "DOC_SYSTEM_DOCS_DIR": "docs"
            }
        },
        "tools": [
            {
                "name": "search_docs",
                "description": "Search documentation using semantic search"
            },
            {
                "name": "find_similar_code",
                "description": "Find similar code implementations"
            },
            {
                "name": "check_dependencies",
                "description": "Check code dependencies"
            },
            {
                "name": "get_file_context",
                "description": "Get complete file documentation"
            },
            {
                "name": "list_api_routes",
                "description": "List all API routes"
            },
            {
                "name": "list_database_models",
                "description": "List all database models"
            },
            {
                "name": "suggest_patterns",
                "description": "Suggest code patterns"
            },
            {
                "name": "analyze_complexity",
                "description": "Analyze code complexity"
            }
        ]
    }
    
    import json
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"{Fore.GREEN}✅ MCP configuration created{Style.RESET_ALL}")

def initial_scan():
    """Perform initial project scan"""
    print(f"\n{Fore.YELLOW}🔍 Performing initial project scan...{Style.RESET_ALL}")
    
    # Check if there are Python files to analyze
    python_files = list(Path('.').rglob('*.py'))
    
    # Exclude virtual environments and cache
    python_files = [
        f for f in python_files 
        if not any(p in str(f) for p in ['venv', '.venv', '__pycache__', 'node_modules'])
    ]
    
    if python_files:
        print(f"{Fore.CYAN}Found {len(python_files)} Python files{Style.RESET_ALL}")
        
        # Ask user if they want to run initial analysis
        if click.confirm("Run initial documentation generation?"):
            print(f"{Fore.YELLOW}🚀 Starting documentation generation...{Style.RESET_ALL}")
            
            try:
                subprocess.run([
                    sys.executable, 
                    "scripts/intelligent_doc_system.py",
                    "--directories", ".",
                    "--parallel"
                ], check=True)
                print(f"{Fore.GREEN}✅ Initial documentation generated{Style.RESET_ALL}")
            except subprocess.CalledProcessError as e:
                print(f"{Fore.YELLOW}⚠️ Documentation generation failed: {e}{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}No Python files found for initial scan{Style.RESET_ALL}")

def print_next_steps():
    """Print next steps for the user"""
    print(f"\n{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🎉 Setup Complete!{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}\n")
    
    print(f"{Fore.GREEN}Next Steps:{Style.RESET_ALL}")
    print(f"1. Generate documentation: {Fore.CYAN}python scripts/intelligent_doc_system.py{Style.RESET_ALL}")
    print(f"2. Start MCP server: {Fore.CYAN}python mcp_server/server.py{Style.RESET_ALL}")
    print(f"3. Start file watcher: {Fore.CYAN}python scripts/intelligent_doc_system.py --watch{Style.RESET_ALL}")
    print(f"4. View documentation: {Fore.CYAN}open docs/PROJECT_OVERVIEW.md{Style.RESET_ALL}")
    
    print(f"\n{Fore.YELLOW}MCP Tools Available:{Style.RESET_ALL}")
    print("  • search_docs - Search documentation")
    print("  • find_similar_code - Find similar implementations")
    print("  • check_dependencies - Check code dependencies")
    print("  • list_api_routes - List API endpoints")
    print("  • list_database_models - List database models")
    print("  • suggest_patterns - Get pattern suggestions")
    print("  • analyze_complexity - Find complex code")
    
    print(f"\n{Fore.MAGENTA}Happy coding! 🚀{Style.RESET_ALL}\n")

@click.command()
@click.option('--skip-deps', is_flag=True, help='Skip dependency installation')
@click.option('--skip-ollama', is_flag=True, help='Skip Ollama setup')
@click.option('--skip-scan', is_flag=True, help='Skip initial project scan')
def main(skip_deps, skip_ollama, skip_scan):
    """Setup Intelligent Documentation System"""
    
    print_header()
    
    # Check Python version
    check_python_version()
    
    # Create directories
    create_directories()
    
    # Install dependencies
    if not skip_deps:
        install_dependencies()
    
    # Setup Ollama
    if not skip_ollama:
        setup_ollama()
    
    # Create configuration files
    create_env_file()
    create_mcp_config()
    
    # Run initial scan
    if not skip_scan:
        initial_scan()
    
    # Print next steps
    print_next_steps()

if __name__ == "__main__":
    main()