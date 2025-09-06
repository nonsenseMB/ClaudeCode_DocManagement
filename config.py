"""
Configuration for AutoDoc system
Allows customization per project
"""

import os
from pathlib import Path
from typing import List, Set, Dict, Any
from dataclasses import dataclass, field

@dataclass
class AutoDocConfig:
    """Configuration for AutoDoc system"""
    
    # Project settings
    project_root: str = "."
    docs_dir: str = "autodoc/autodoc_docs"  # Changed to be inside autodoc folder
    vector_db_dir: str = "autodoc/autodoc_vector_db"  # Changed to be inside autodoc folder
    
    # LLM settings
    llm_model: str = "codellama:7b"
    llm_enabled: bool = True
    llm_temperature: float = 0.3
    
    # File watching
    watch_directories: List[str] = field(default_factory=lambda: ["src", "app", "lib"])
    watch_debounce_seconds: int = 2
    
    # Processing
    parallel_processing: bool = True
    max_workers: int = 4
    
    # Ignored patterns
    ignored_patterns: Set[str] = field(default_factory=lambda: {
        '__pycache__', '.pytest_cache', '.git', 'venv', '.venv',
        'node_modules', '__init__.py', 'migrations', '.pyc',
        'autodoc', 'autodoc_docs', 'autodoc_vector_db'
    })
    
    # MCP Server
    mcp_server_port: int = 3015  # Using 3010-3020 range to avoid conflicts
    mcp_server_host: str = "localhost"
    
    # Embedding model (optimized for code)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"  # Reliable and fast
    
    @classmethod
    def from_env(cls) -> 'AutoDocConfig':
        """Create config from environment variables"""
        config = cls()
        
        # Override with env vars if present
        if os.getenv('AUTODOC_PROJECT_ROOT'):
            config.project_root = os.getenv('AUTODOC_PROJECT_ROOT', '.')
        if os.getenv('AUTODOC_DOCS_DIR'):
            config.docs_dir = os.getenv('AUTODOC_DOCS_DIR', 'autodoc_docs')
        if os.getenv('AUTODOC_VECTOR_DB_DIR'):
            config.vector_db_dir = os.getenv('AUTODOC_VECTOR_DB_DIR', 'autodoc_vector_db')
        if os.getenv('AUTODOC_LLM_MODEL'):
            config.llm_model = os.getenv('AUTODOC_LLM_MODEL', 'codellama:7b')
        if os.getenv('AUTODOC_LLM_ENABLED'):
            llm_enabled_str = os.getenv('AUTODOC_LLM_ENABLED', 'true')
            config.llm_enabled = llm_enabled_str.lower() == 'true'
        if os.getenv('AUTODOC_WATCH_DIRS'):
            watch_dirs = os.getenv('AUTODOC_WATCH_DIRS', 'src,app,lib')
            config.watch_directories = watch_dirs.split(',')
        if os.getenv('AUTODOC_MAX_WORKERS'):
            max_workers_str = os.getenv('AUTODOC_MAX_WORKERS', '4')
            config.max_workers = int(max_workers_str)
            
        return config
    
    @classmethod
    def from_file(cls, config_file: str = "autodoc.config.json") -> 'AutoDocConfig':
        """Load config from JSON file"""
        import json
        
        config_path = Path(config_file)
        if not config_path.exists():
            return cls()
        
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        return cls(**config_data)
    
    def to_file(self, config_file: str = "autodoc.config.json"):
        """Save config to JSON file"""
        import json
        from dataclasses import asdict
        
        config_data = asdict(self)
        # Convert sets to lists for JSON serialization
        config_data['ignored_patterns'] = list(config_data['ignored_patterns'])
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def get_absolute_paths(self) -> Dict[str, Path]:
        """Get absolute paths for directories"""
        root = Path(self.project_root).resolve()
        return {
            'project_root': root,
            'docs_dir': root / self.docs_dir,
            'vector_db_dir': root / self.vector_db_dir
        }