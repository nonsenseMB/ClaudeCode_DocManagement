#!/bin/bash
#
# AutoDoc Setup Script mit Virtual Environment
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_NAME="autodoc_venv"
VENV_PATH="$SCRIPT_DIR/$VENV_NAME"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${MAGENTA}============================================================${NC}"
echo -e "${CYAN}🤖 AutoDoc Setup with Virtual Environment${NC}"
echo -e "${MAGENTA}============================================================${NC}\n"

# Check Python version
echo -e "${YELLOW}📦 Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}❌ Python 3.8+ required. Current: $PYTHON_VERSION${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python $PYTHON_VERSION detected${NC}"

# Create virtual environment
echo -e "\n${YELLOW}🔧 Creating virtual environment...${NC}"
if [ -d "$VENV_PATH" ]; then
    echo -e "${CYAN}Virtual environment already exists at $VENV_PATH${NC}"
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_PATH"
        python3 -m venv "$VENV_PATH"
        echo -e "${GREEN}✅ Virtual environment recreated${NC}"
    fi
else
    python3 -m venv "$VENV_PATH"
    echo -e "${GREEN}✅ Virtual environment created at $VENV_PATH${NC}"
fi

# Activate virtual environment
echo -e "\n${YELLOW}🚀 Activating virtual environment...${NC}"
source "$VENV_PATH/bin/activate"
echo -e "${GREEN}✅ Virtual environment activated${NC}"

# Upgrade pip
echo -e "\n${YELLOW}📦 Upgrading pip...${NC}"
pip install --upgrade pip --quiet
echo -e "${GREEN}✅ Pip upgraded${NC}"

# Install dependencies
echo -e "\n${YELLOW}📦 Installing AutoDoc dependencies...${NC}"
pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
echo -e "${GREEN}✅ Dependencies installed${NC}"

# Install better code embedding model
echo -e "\n${YELLOW}🧠 Installing optimized code embedding model...${NC}"
pip install transformers --quiet
echo -e "${GREEN}✅ Code embedding support installed${NC}"

# Check Ollama (optional)
echo -e "\n${YELLOW}🤖 Checking Ollama installation...${NC}"
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}✅ Ollama detected${NC}"
    if ollama list 2>/dev/null | grep -q "codellama"; then
        echo -e "${GREEN}✅ CodeLlama model available${NC}"
    else
        echo -e "${YELLOW}⚠️ CodeLlama model not found${NC}"
        echo -e "   Install with: ${CYAN}ollama pull codellama:7b${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ Ollama not installed (optional)${NC}"
    echo -e "   Install from: ${CYAN}https://ollama.ai${NC}"
fi

# Detect project structure
echo -e "\n${YELLOW}🔍 Detecting project structure...${NC}"
DETECTED_DIRS=()

# Common Python project directories
for dir in src app lib backend frontend services api core utils scripts tests; do
    if [ -d "$PROJECT_ROOT/$dir" ]; then
        DETECTED_DIRS+=("$dir")
        echo -e "   ${GREEN}✓${NC} Found: $dir/"
    fi
done

if [ ${#DETECTED_DIRS[@]} -eq 0 ]; then
    echo -e "${YELLOW}   No standard directories found. Will scan entire project.${NC}"
    DETECTED_DIRS=(".")
fi

# Create activation script
echo -e "\n${YELLOW}📝 Creating activation script...${NC}"
cat > "$SCRIPT_DIR/activate.sh" << 'EOF'
#!/bin/bash
# AutoDoc Environment Activation

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/autodoc_venv"

if [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
    echo "✅ AutoDoc environment activated"
    echo "Available commands:"
    echo "  autodoc init     - Initialize in current project"
    echo "  autodoc scan     - Scan and document code"
    echo "  autodoc watch    - Watch for changes"
    echo "  autodoc server   - Start MCP server"
    echo "  autodoc info     - Show system info"
else
    echo "❌ Virtual environment not found. Run setup.sh first."
    exit 1
fi

# Add autodoc CLI to PATH
export PATH="$SCRIPT_DIR:$PATH"
alias autodoc="python $SCRIPT_DIR/cli.py"
EOF

chmod +x "$SCRIPT_DIR/activate.sh"
echo -e "${GREEN}✅ Activation script created${NC}"

# Create default config with detected directories
echo -e "\n${YELLOW}⚙️ Creating default configuration...${NC}"
cat > "$PROJECT_ROOT/autodoc.config.json" << EOF
{
  "project_root": ".",
  "docs_dir": "autodoc_docs",
  "vector_db_dir": "autodoc_vector_db",
  "llm_model": "codellama:7b",
  "llm_enabled": true,
  "watch_directories": [$(printf '"%s",' "${DETECTED_DIRS[@]}" | sed 's/,$//'))],
  "watch_debounce_seconds": 2,
  "parallel_processing": true,
  "max_workers": 4,
  "mcp_server_port": 3015,
  "embedding_model": "microsoft/codebert-base",
  "ignored_patterns": [
    "__pycache__", ".pytest_cache", ".git", "venv", ".venv",
    "node_modules", "__init__.py", "migrations", ".pyc",
    "autodoc", "autodoc_docs", "autodoc_vector_db", "autodoc_venv"
  ]
}
EOF
echo -e "${GREEN}✅ Configuration created with detected directories${NC}"

# Update .gitignore
echo -e "\n${YELLOW}📝 Updating .gitignore...${NC}"
if [ -f "$PROJECT_ROOT/.gitignore" ]; then
    if ! grep -q "# AutoDoc" "$PROJECT_ROOT/.gitignore"; then
        cat >> "$PROJECT_ROOT/.gitignore" << EOF

# AutoDoc
autodoc_docs/
autodoc_vector_db/
autodoc/autodoc_venv/
*.pyc
__pycache__/
EOF
        echo -e "${GREEN}✅ .gitignore updated${NC}"
    else
        echo -e "${CYAN}ℹ️ .gitignore already contains AutoDoc entries${NC}"
    fi
fi

# Print summary
echo -e "\n${MAGENTA}============================================================${NC}"
echo -e "${GREEN}🎉 Setup Complete!${NC}"
echo -e "${MAGENTA}============================================================${NC}\n"

echo -e "${CYAN}Virtual Environment:${NC} $VENV_PATH"
echo -e "${CYAN}Detected Directories:${NC} ${DETECTED_DIRS[*]}"
echo -e "${CYAN}MCP Server Port:${NC} 3015"
echo -e "${CYAN}Embedding Model:${NC} microsoft/codebert-base"

echo -e "\n${YELLOW}Next Steps:${NC}"
echo -e "1. Activate environment: ${GREEN}source autodoc/activate.sh${NC}"
echo -e "2. Initial scan: ${GREEN}autodoc scan${NC}"
echo -e "3. Start MCP server: ${GREEN}autodoc server${NC}"
echo -e "4. Start file watcher: ${GREEN}autodoc watch${NC}"

echo -e "\n${CYAN}Tip: Add this to your shell profile for easy activation:${NC}"
echo -e "   ${GREEN}alias autodoc-env='source $(pwd)/autodoc/activate.sh'${NC}"