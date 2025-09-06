# 🤖 AutoDoc - Portable Intelligent Documentation System

**Verhindert Code-Redundanzen und Inkonsistenzen durch semantische Suche und automatische Dokumentation.**

## ✨ Features

- 🔍 **Semantische Code-Suche** - Findet ähnliche Implementierungen mit ChromaDB
- 📝 **Multi-Language Support** - Python, JavaScript, TypeScript, React, Node.js
- 🔄 **Real-time Updates** - File-Watcher aktualisiert Docs automatisch
- 🌐 **MCP Server Integration** - Direkte Tools in Claude Code verfügbar
- 📦 **Vollständig Portabel** - Ein Ordner, zwischen Projekten kopierbar
- 🎯 **Framework-Erkennung** - FastAPI, Flask, Django, React, Vue, Angular, Express
- 🔒 **Sichere Filterung** - Ignoriert .env, venv, node_modules, secrets automatisch

## 🚀 Quick Installation

### Option 1: Kopieren & Loslegen
```bash
# 1. AutoDoc in dein Projekt kopieren
cp -r /path/to/autodoc ./autodoc

# 2. Dependencies installieren
pip install -r autodoc/requirements.txt

# 3. AutoDoc initialisieren
python autodoc/cli.py init

# 4. Erste Analyse
python autodoc/cli.py scan
```

### Option 2: Als Git Submodule
```bash
# AutoDoc als Submodule hinzufügen
git submodule add https://github.com/yourrepo/autodoc.git autodoc

# Dependencies installieren
pip install -r autodoc/requirements.txt

# Initialisieren
python autodoc/cli.py init
```

### Option 3: Globale Installation
```bash
# AutoDoc global installieren
cd autodoc
pip install -e .

# Dann in jedem Projekt verfügbar
autodoc init
autodoc scan
```

## 📖 Verwendung

### 1. Projekt initialisieren
```bash
python autodoc/cli.py init
```
Erstellt Konfiguration und Verzeichnisse.

### 2. Code analysieren
```bash
python autodoc/cli.py scan -d src -d lib
```
Scannt angegebene Verzeichnisse und generiert Dokumentation.

### 3. MCP Server starten (für Claude Code)
```bash
python autodoc/cli.py server
```
Startet MCP Server auf Port 3000.

### 4. File-Watcher aktivieren
```bash
python autodoc/cli.py watch --scan-first
```
Überwacht Änderungen und aktualisiert Docs automatisch.

### 5. Dokumentation durchsuchen
```bash
python autodoc/cli.py search "authentication"
```
Testet die semantische Suche.

## 🛠️ MCP Tools für Claude Code

Nach Start des MCP Servers stehen diese Tools zur Verfügung:

| Tool | Beschreibung | Beispiel |
|------|--------------|----------|
| `search_docs` | Semantische Suche | `search_docs("user authentication")` |
| `find_similar_code` | Ähnliche Implementierungen | `find_similar_code("validate email")` |
| `check_dependencies` | Abhängigkeiten prüfen | `check_dependencies("UserModel")` |
| `get_file_context` | Datei-Dokumentation | `get_file_context("src/auth.py")` |
| `list_api_routes` | API-Endpunkte | `list_api_routes()` |
| `list_database_models` | DB-Models | `list_database_models()` |
| `suggest_patterns` | Pattern-Vorschläge | `suggest_patterns("create endpoint")` |
| `analyze_complexity` | Komplexe Areas | `analyze_complexity(threshold=10)` |

## ⚙️ Konfiguration

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

### Unterstützte Sprachen & Frameworks

| Sprache | Dateitypen | Frameworks | Features |
|---------|------------|------------|----------|
| **Python** | .py | FastAPI, Flask, Django, SQLAlchemy | AST-Analyse, Komplexität, Decorators |
| **JavaScript** | .js, .jsx | React, Vue, Express, Node.js | Funktionen, Komponenten, API-Calls |
| **TypeScript** | .ts, .tsx | React, Angular, NestJS | Interfaces, Types, Generics |

### Automatische Erkennung
- **Sprache**: Erkennt automatisch Python/JS/TS Projekte
- **Frameworks**: Identifiziert verwendete Frameworks
- **Verzeichnisse**: Scannt alle relevanten Ordner im Root
- **Filterung**: Ignoriert automatisch sensitive Dateien

## 📁 Generierte Struktur

```
your_project/
├── autodoc/                    # AutoDoc System (portable)
│   ├── core/                   # Kern-Komponenten
│   │   ├── doc_system.py       # Haupt-System
│   │   └── js_analyzer.py      # JavaScript Analyzer
│   ├── mcp_server/             # MCP Server
│   ├── scripts/                # Utility Scripts
│   ├── cli.py                  # CLI Interface
│   ├── config.py               # Konfiguration
│   └── utils.py                # Utilities & Detection
├── autodoc_docs/               # Generierte Dokumentation
│   ├── files/                  # Datei-Docs
│   ├── PROJECT_OVERVIEW.md     # Übersicht
│   └── file_metadata.json      # Metadaten
├── autodoc_vector_db/          # ChromaDB Storage
└── autodoc_venv/               # Virtual Environment

## 🔄 Integration in bestehende Projekte

### 1. CLAUDE.md Integration
Füge zu deiner CLAUDE.md hinzu:
```markdown
## 🔴 PFLICHT: AutoDoc verwenden

BEVOR Code erstellt wird:
1. `search_docs "[feature]"` - Existierende Lösungen suchen
2. `find_similar_code "[beschreibung]"` - Ähnliche Patterns finden  
3. `suggest_patterns "[kontext]"` - Best Practices abrufen
4. `check_dependencies "[modul]"` - Impact analysieren

KEINE Code-Erstellung ohne vorherige Suche!
```

### 2. CI/CD Integration
```yaml
# .github/workflows/autodoc.yml
name: Update Documentation
on:
  push:
    paths:
      - '**.py'
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
python autodoc/cli.py scan --directories $(git diff --cached --name-only | grep ".py$" | xargs dirname | sort -u)
```

## 🐛 Troubleshooting

### Problem: Ollama nicht verfügbar
```bash
# Ollama installieren
curl -fsSL https://ollama.ai/install.sh | sh

# CodeLlama Model laden
ollama pull codellama:7b

# Oder LLM deaktivieren in config
"llm_enabled": false
```

### Problem: ChromaDB Fehler
```bash
# Vector DB neu aufbauen
rm -rf autodoc_vector_db/
python autodoc/cli.py scan
```

### Problem: Import Fehler
```bash
# Sicherstellen dass alle Dependencies installiert sind
pip install -r autodoc/requirements.txt

# Python Path prüfen
export PYTHONPATH="${PYTHONPATH}:$(pwd)/autodoc"
```

### Problem: MCP Server startet nicht
```bash
# Mit Debug Output
python -u autodoc/mcp_server/server.py

# Permissions prüfen
chmod +x autodoc/cli.py
chmod +x autodoc/mcp_server/server.py
```

## 🎯 Best Practices

### DO's ✅
- **Immer erst suchen** bevor neuer Code erstellt wird
- **Manual Context** in Docs für wichtige Entscheidungen pflegen
- **File-Watcher** laufen lassen während Entwicklung
- **Regelmäßig** `analyze_complexity` für Refactoring-Targets nutzen

### DON'Ts ❌
- Keine Secrets in Dokumentation schreiben
- Nicht autodoc_docs/ ins Git committen (zu .gitignore)
- Vector DB nicht zwischen verschiedenen Projekten teilen
- LLM nicht für sensitive Codebases verwenden

## 📊 Performance

- **Initiale Analyse**: ~1-2 Sekunden pro Datei
- **Semantische Suche**: <100ms Response
- **File-Watcher**: 2 Sekunden Debouncing
- **Vector DB Größe**: ~15MB für 1000 Dateien
- **Memory Usage**: ~200-500MB während Analyse

## 🔐 Sicherheit & Datenschutz

### Automatisch ignorierte Dateien/Ordner
- **Secrets**: `.env`, `.env.*`, `*.key`, `*.pem`, credentials
- **Virtual Envs**: `venv`, `.venv`, `*_venv`, conda environments
- **Dependencies**: `node_modules`, `vendor`, `bower_components`
- **Build/Cache**: `dist`, `build`, `__pycache__`, `.cache`
- **Sensitive**: Private keys, tokens, passwords

### Sicherheitsfeatures
- Alle Daten bleiben **lokal** (keine Cloud)
- Read-only Analyse (keine Code-Modifikation)
- Comprehensive Ignore Patterns (280+ patterns)
- Optional: LLM kann deaktiviert werden
- Kein Zugriff auf System-Credentials

## 🤝 Mitwirken

AutoDoc ist ein offenes System. Verbesserungsvorschläge willkommen!

### Neue Framework-Unterstützung
Erweitere `CodeAnalyzer.framework_patterns` in `core/doc_system.py`.

### Neue MCP Tools
Füge neue Tools in `mcp_server/server.py` hinzu.

### Bessere Embeddings
Tausche Model in `SemanticIndexer.__init__` aus.

## 📝 Lizenz

MIT License - Frei verwendbar in allen Projekten.

## 🙏 Credits

Entwickelt zur Lösung von Claude Code Kontext-Problemen in großen Projekten.

---

**Tipp**: Nach Installation immer zuerst `autodoc info` ausführen um Status zu prüfen!