# 🤖 AutoDoc - Portable Intelligent Documentation System

**Prevents code redundancy and inconsistencies through semantic search and automatic documentation.**

## ✨ Features

- 🔍 **Semantic Code Search** - Finds similar implementations using ChromaDB
- 📝 **Multi-Language Support** - Python, JavaScript, TypeScript, React, Node.js
- 🔄 **Real-time Updates** - File watcher updates docs automatically
- 🌐 **MCP Server Integration** - Direct tools available in Claude Code
- 📦 **Fully Portable** - Single folder, copy between projects
- 🎯 **Framework Detection** - FastAPI, Flask, Django, React, Vue, Angular, Express
- 🔒 **Secure Filtering** - Automatically ignores .env, venv, node_modules, secrets

## 🚀 Quick Installation

### Option 1: Copy & Go
```bash
# 1. Copy AutoDoc to your project
cp -r /path/to/autodoc ./autodoc

# 2. Install dependencies
pip install -r autodoc/requirements.txt

# 3. Initialize AutoDoc
python autodoc/cli.py init

# 4. Run initial scan
python autodoc/cli.py scan
```

### Option 2: As Git Submodule
```bash
# Add AutoDoc as submodule
git submodule add https://github.com/nonsenseMB/ClaudeCode_DocManagement.git autodoc

# Install dependencies
pip install -r autodoc/requirements.txt

# Initialize
python autodoc/cli.py init
```

### Option 3: Global Installation
```bash
# Install AutoDoc globally
cd autodoc
pip install -e .

# Then available in any project
autodoc init
autodoc scan
```

## 📖 Usage

### 1. Initialize Project
```bash
python autodoc/cli.py init
```
Creates configuration and directories.

### 2. Analyze Code
```bash
python autodoc/cli.py scan -d src -d lib
```
Scans specified directories and generates documentation.

### 3. Start MCP Server (for Claude Code)
```bash
python autodoc/cli.py server
```
Starts MCP server on port 3015.

### 4. Enable File Watcher
```bash
python autodoc/cli.py watch --scan-first
```
Monitors changes and updates docs automatically.

### 5. Search Documentation
```bash
python autodoc/cli.py search "authentication"
```
Tests semantic search functionality.

## 🛠️ MCP Tools for Claude Code

After starting the MCP server, these tools become available:

| Tool | Description | Example |
|------|-------------|---------|
| `search_docs` | Semantic search | `search_docs("user authentication")` |
| `find_similar_code` | Similar implementations | `find_similar_code("validate email")` |
| `check_dependencies` | Check dependencies | `check_dependencies("UserModel")` |
| `get_file_context` | File documentation | `get_file_context("src/auth.py")` |
| `list_api_routes` | API endpoints | `list_api_routes()` |
| `list_database_models` | DB models | `list_database_models()` |
| `suggest_patterns` | Pattern suggestions | `suggest_patterns("create endpoint")` |
| `analyze_complexity` | Complex areas | `analyze_complexity(threshold=10)` |

## ⚙️ Configuration

### autodoc.config.json
```json
{
  "project_root": ".",
  "docs_dir": "autodoc_docs",
  "vector_db_dir": "autodoc_vector_db",
  "llm_model": "codellama:7b",
  "llm_enabled": true,
  "watch_directories": ["src", "app", "lib"],
  "watch_debounce_seconds": 2,
  "parallel_processing": true,
  "max_workers": 4,
  "mcp_server_port": 3015,
  "embedding_model": "microsoft/codebert-base",
  "ignored_patterns": [
    "__pycache__", "venv", "node_modules", "autodoc"
  ]
}
```

### Environment Variables
```bash
export AUTODOC_PROJECT_ROOT=.
export AUTODOC_DOCS_DIR=autodoc_docs
export AUTODOC_VECTOR_DB_DIR=autodoc_vector_db
export AUTODOC_LLM_MODEL=codellama:7b
export AUTODOC_WATCH_DIRS=src,app,lib
export AUTODOC_MAX_WORKERS=4
```

## 🌍 Multi-Language Support

### Supported Languages & Frameworks

| Language | File Types | Frameworks | Features |
|----------|------------|------------|----------|
| **Python** | .py | FastAPI, Flask, Django, SQLAlchemy | AST analysis, complexity, decorators |
| **JavaScript** | .js, .jsx | React, Vue, Express, Node.js | Functions, components, API calls |
| **TypeScript** | .ts, .tsx | React, Angular, NestJS | Interfaces, types, generics |

### Automatic Detection
- **Language**: Automatically detects Python/JS/TS projects
- **Frameworks**: Identifies used frameworks
- **Directories**: Scans all relevant folders in root
- **Filtering**: Automatically ignores sensitive files

## 📁 Generated Structure

```
your_project/
├── autodoc/                    # AutoDoc system (portable & self-contained)
│   ├── core/                   # Core components
│   │   ├── doc_system.py       # Main system
│   │   └── js_analyzer.py      # JavaScript analyzer
│   ├── mcp_server/             # MCP server
│   ├── scripts/                # Utility scripts
│   ├── cli.py                  # CLI interface
│   ├── config.py               # Configuration
│   ├── utils.py                # Utilities & detection
│   ├── autodoc_docs/           # Generated documentation (inside autodoc/)
│   │   ├── files/              # File docs
│   │   ├── PROJECT_OVERVIEW.md # Overview
│   │   └── file_metadata.json  # Metadata
│   ├── autodoc_vector_db/      # ChromaDB storage (inside autodoc/)
│   ├── autodoc.config.json     # Configuration file (inside autodoc/)
│   └── autodoc_venv/           # Virtual environment (inside autodoc/)
└── .gitignore                  # Should include autodoc/autodoc_*
```

**Important**: All generated files stay within the `autodoc/` folder for true portability!

## 🔄 Integration with Existing Projects

### 1. CLAUDE.md Integration
Add to your CLAUDE.md:
```markdown
## 🔴 MANDATORY: Use AutoDoc

BEFORE creating code:
1. `search_docs "[feature]"` - Search existing solutions
2. `find_similar_code "[description]"` - Find similar patterns  
3. `suggest_patterns "[context]"` - Get best practices
4. `check_dependencies "[module]"` - Analyze impact

NO code creation without prior search!
```

### 2. CI/CD Integration
```yaml
# .github/workflows/autodoc.yml
name: Update Documentation
on:
  push:
    paths:
      - '**.py'
      - '**.js'
      - '**.ts'
jobs:
  update-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
      - name: Install AutoDoc
        run: pip install -r autodoc/requirements.txt
      - name: Generate Docs
        run: python autodoc/cli.py scan
      - name: Upload Docs
        uses: actions/upload-artifact@v2
        with:
          name: documentation
          path: autodoc_docs/
```

### 3. Pre-Commit Hook
```bash
#!/bin/sh
# .git/hooks/pre-commit
python autodoc/cli.py scan --directories $(git diff --cached --name-only | grep -E "\.(py|js|ts)$" | xargs dirname | sort -u)
```

## 🐛 Troubleshooting

### Problem: Ollama not available
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Load CodeLlama model
ollama pull codellama:7b

# Or disable LLM in config
"llm_enabled": false
```

### Problem: ChromaDB errors
```bash
# Rebuild vector DB
rm -rf autodoc_vector_db/
python autodoc/cli.py scan
```

### Problem: Import errors
```bash
# Ensure all dependencies are installed
pip install -r autodoc/requirements.txt

# Check Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/autodoc"
```

### Problem: MCP server won't start
```bash
# Run with debug output
python -u autodoc/mcp_server/server.py

# Check permissions
chmod +x autodoc/cli.py
chmod +x autodoc/mcp_server/server.py
```

## 🎯 Best Practices

### DO's ✅
- **Always search first** before creating new code
- **Maintain manual context** in docs for important decisions
- **Keep file watcher running** during development
- **Regularly use** `analyze_complexity` for refactoring targets
- **Update ignored patterns** for project-specific sensitive files

### DON'Ts ❌
- Don't commit autodoc_docs/ to git (add to .gitignore)
- Don't share vector DB between different projects
- Don't use LLM for sensitive codebases
- Don't ignore AutoDoc warnings about code redundancy
- Don't create code without checking existing patterns

## 📊 Performance

- **Initial Analysis**: ~1-2 seconds per file
- **Semantic Search**: <100ms response time
- **File Watcher**: 2 second debouncing
- **Vector DB Size**: ~15MB for 1000 files
- **Memory Usage**: ~200-500MB during analysis

## 🔐 Security & Privacy

### Automatically Ignored Files/Folders
- **Secrets**: `.env`, `.env.*`, `*.key`, `*.pem`, credentials
- **Virtual Envs**: `venv`, `.venv`, `*_venv`, conda environments
- **Dependencies**: `node_modules`, `vendor`, `bower_components`
- **Build/Cache**: `dist`, `build`, `__pycache__`, `.cache`
- **Sensitive**: Private keys, tokens, passwords

### Security Features
- All data stays **local** (no cloud)
- Read-only analysis (no code modification)
- Comprehensive ignore patterns (280+ patterns)
- Optional: LLM can be disabled
- No access to system credentials

## 🤝 Contributing

AutoDoc is an open system. Improvements are welcome!

### Adding New Framework Support
Extend `CodeAnalyzer.framework_patterns` in `core/doc_system.py`.

### Adding New MCP Tools
Add new tools in `mcp_server/server.py`.

### Better Embeddings
Replace model in `SemanticIndexer.__init__`.

## 📝 License

MIT License - Free to use in all projects.

## 🙏 Credits

Developed to solve Claude Code context problems in large projects.

---

**Tip**: After installation, always run `autodoc info` first to check status!