"""
Utility functions for AutoDoc
"""

import os
from pathlib import Path
from typing import List, Set
import logging

logger = logging.getLogger(__name__)


def detect_project_directories(project_root: str = ".", language: str = "auto") -> List[str]:
    """
    Automatically detect relevant directories in a project
    
    Args:
        project_root: Root directory of project
        language: 'python', 'javascript', 'auto' (detect automatically)
    
    Returns:
        List of directory paths relative to project root
    """
    root = Path(project_root).resolve()
    detected_dirs = []
    
    # Detect language if auto
    if language == "auto":
        has_python = list(root.glob("**/*.py"))
        has_js = list(root.glob("**/*.js")) or list(root.glob("**/*.jsx"))
        has_ts = list(root.glob("**/*.ts")) or list(root.glob("**/*.tsx"))
        
        is_python = bool(has_python)
        is_javascript = bool(has_js or has_ts)
    else:
        is_python = language == "python"
        is_javascript = language in ["javascript", "typescript", "nodejs", "react"]
    
    # Common directories for all languages
    common_dirs = {
        'src', 'lib', 'core', 'utils', 'scripts',
        'tests', 'test', 'spec', 'specs', 'config'
    }
    
    # Python-specific directories
    python_dirs = {
        'app', 'backend', 'services', 'api',
        'models', 'views', 'controllers', 'handlers',
        'modules', 'packages', 'plugins',
        'routers', 'routes', 'endpoints', 'blueprints',
        'apps', 'management', 'migrations', 'templates',
        'notebooks', 'data', 'experiments', 'pipelines'
    }
    
    # JavaScript/TypeScript/React directories
    javascript_dirs = {
        'frontend', 'client', 'public', 'pages', 'components',
        'hooks', 'contexts', 'reducers', 'actions', 'store',
        'styles', 'assets', 'static', 'layouts', 'features',
        'api', 'services', 'utils', 'helpers', 'constants',
        'middleware', 'controllers', 'routes', 'models'
    }
    
    # Combine relevant directories based on language
    all_dirs = common_dirs.copy()
    if is_python:
        all_dirs.update(python_dirs)
    if is_javascript:
        all_dirs.update(javascript_dirs)
    
    # Check for these directories
    for dir_name in all_dirs:
        dir_path = root / dir_name
        if dir_path.is_dir() and not dir_name.startswith('.'):
            # Check if directory contains relevant files
            if is_python:
                relevant_files = list(dir_path.glob('**/*.py'))
            if is_javascript:
                js_files = list(dir_path.glob('**/*.js')) + list(dir_path.glob('**/*.jsx'))
                ts_files = list(dir_path.glob('**/*.ts')) + list(dir_path.glob('**/*.tsx'))
                relevant_files = js_files + ts_files
            
            if relevant_files:
                detected_dirs.append(dir_name)
                logger.info(f"Detected directory: {dir_name} ({len(relevant_files)} files)")
    
    # If no standard directories found, scan all directories in root
    if not detected_dirs:
        ignore_patterns = get_comprehensive_ignore_patterns()
        
        for item in root.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Skip ignored directories
                if should_ignore_path(item.name, ignore_patterns):
                    continue
                
                # Check for relevant files
                if is_python:
                    relevant_files = list(item.glob('**/*.py'))
                if is_javascript:
                    js_files = list(item.glob('**/*.js')) + list(item.glob('**/*.jsx'))
                    ts_files = list(item.glob('**/*.ts')) + list(item.glob('**/*.tsx'))
                    relevant_files = js_files + ts_files
                
                if relevant_files:
                    detected_dirs.append(item.name)
                    logger.info(f"Found directory with code files: {item.name}")
    
    # If still no directories, scan current directory
    if not detected_dirs:
        detected_dirs.append('.')
        logger.info(f"No subdirectories found, will scan root directory")
    
    return sorted(detected_dirs)


def analyze_project_structure(project_root: str = ".") -> dict:
    """
    Analyze project structure and provide insights
    
    Returns:
        Dictionary with project analysis
    """
    root = Path(project_root).resolve()
    analysis = {
        'directories': detect_project_directories(project_root),
        'framework': detect_framework(root),
        'total_python_files': 0,
        'total_lines': 0,
        'has_tests': False,
        'has_requirements': False,
        'has_setup_py': False,
        'is_package': False
    }
    
    # Count Python files and lines
    for py_file in root.rglob('*.py'):
        if '__pycache__' not in str(py_file) and 'venv' not in str(py_file):
            analysis['total_python_files'] += 1
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    analysis['total_lines'] += len(f.readlines())
            except:
                pass
    
    # Check for common files
    analysis['has_tests'] = any(root.rglob('test*.py')) or (root / 'tests').exists()
    analysis['has_requirements'] = (root / 'requirements.txt').exists()
    analysis['has_setup_py'] = (root / 'setup.py').exists()
    analysis['is_package'] = (root / '__init__.py').exists()
    
    return analysis


def detect_framework(project_root: Path) -> str:
    """
    Detect the framework used in the project
    
    Returns:
        Name of detected framework or 'unknown'
    """
    # Check for framework-specific files or imports
    framework_indicators = {
        'fastapi': ['main.py', 'routers/', 'from fastapi import'],
        'flask': ['app.py', 'blueprints/', 'from flask import'],
        'django': ['manage.py', 'settings.py', 'from django.'],
        'streamlit': ['streamlit', 'st.', 'import streamlit'],
        'jupyter': ['.ipynb', 'notebooks/'],
        'pytest': ['conftest.py', 'pytest.ini', 'import pytest'],
    }
    
    for framework, indicators in framework_indicators.items():
        for indicator in indicators:
            if '/' in indicator:
                # Check for directory
                if (project_root / indicator.rstrip('/')).exists():
                    return framework
            elif '.' in indicator and not indicator.endswith('.py'):
                # Check for file extension
                if list(project_root.rglob(f'*{indicator}')):
                    return framework
            elif 'import' in indicator or 'from' in indicator:
                # Check for import statements
                for py_file in project_root.rglob('*.py'):
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if indicator in content:
                                return framework
                    except:
                        continue
            else:
                # Check for specific file
                if (project_root / indicator).exists():
                    return framework
    
    return 'python'  # Default to generic Python project


def get_comprehensive_ignore_patterns() -> Set[str]:
    """
    Get comprehensive list of patterns to ignore for security and efficiency
    
    Returns:
        Set of patterns to ignore
    """
    return {
        # Environment and secrets
        '.env', '.env.*', '*.env', 'env', '.envrc', 'secrets', '.secrets',
        '*.key', '*.pem', '*.crt', '*.cer', '*.p12', '*.pfx',
        'credentials', 'credentials.json', 'token.json',
        
        # Python
        '__pycache__', '*.pyc', '*.pyo', '*.pyd', '.Python',
        'pip-log.txt', 'pip-delete-this-directory.txt',
        '*.so', '*.dylib', '*.dll',
        
        # Virtual environments (comprehensive)
        'venv', '.venv', 'env', 'ENV', 'env.bak', 'venv.bak',
        'virtualenv', 'pyenv', '.python-version', 'Pipenv',
        'conda-env', 'miniconda', 'anaconda',
        '*_venv', 'venv_*', '.virtualenv', 'virtualenvs',
        
        # Node.js / JavaScript
        'node_modules', '.npm', '.yarn', '.pnp.js', '.pnp',
        'npm-debug.log*', 'yarn-debug.log*', 'yarn-error.log*',
        '.next', '.nuxt', '.cache', '.parcel-cache',
        'dist', 'build', 'out', '.webpack',
        
        # Testing & Coverage
        '.pytest_cache', '.coverage', 'htmlcov', '.tox', '.hypothesis',
        'coverage', '*.cover', '.nyc_output', 'test-results',
        
        # IDEs and Editors
        '.vscode', '.idea', '*.swp', '*.swo', '*~', '.DS_Store',
        '*.sublime-*', '.project', '.classpath', '*.iml',
        '.settings', 'nbproject', '.netbeans', '.eclipse',
        
        # Build artifacts
        'build', 'dist', '*.egg-info', '*.egg', 'wheels',
        'target', 'bin', 'obj', '*.class', '*.jar',
        '_build', '.gradle', '.mvn',
        
        # Documentation
        'docs/_build', 'site', '_site', 'gh-pages',
        
        # Version control
        '.git', '.svn', '.hg', '.bzr', '_darcs', '.fossil',
        
        # Databases and storage
        '*.db', '*.sqlite', '*.sqlite3', '*.mongodb',
        'database', 'databases', 'db_data', 'postgres_data',
        '*.rdb', 'dump.rdb',
        
        # Logs and temporary files
        '*.log', 'logs', 'log', '*.tmp', 'tmp', 'temp',
        '*.bak', '*.backup', '*.old', '*.orig',
        '*.pid', '*.seed', '*.pid.lock',
        
        # AutoDoc specific
        'autodoc_docs', 'autodoc_vector_db', 'autodoc_venv',
        'autodoc', '.autodoc',
        
        # Cache directories
        '.cache', 'cache', '__pycache__', '.mypy_cache',
        '.ruff_cache', '.hypothesis', '.nox', '.pants.d',
        
        # OS specific
        'Thumbs.db', 'desktop.ini', '$RECYCLE.BIN',
        '*.lnk', 'System Volume Information',
        
        # Package managers
        'bower_components', 'jspm_packages', 'vendor',
        
        # Sensitive data patterns
        '*_secret*', '*_private*', '*.secret', '*.private',
        'id_rsa*', 'id_dsa*', 'id_ecdsa*', 'id_ed25519*',
        '*.ppk', 'known_hosts', 'authorized_keys'
    }

def should_ignore_path(path: str, ignore_patterns: Set[str]) -> bool:
    """
    Check if a path should be ignored based on patterns
    
    Args:
        path: Path to check
        ignore_patterns: Set of patterns to match against
        
    Returns:
        True if path should be ignored
    """
    import fnmatch
    
    path_lower = path.lower()
    
    for pattern in ignore_patterns:
        # Direct match
        if path == pattern or path_lower == pattern.lower():
            return True
        
        # Wildcard match
        if '*' in pattern:
            if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path_lower, pattern.lower()):
                return True
        
        # Check if path starts with pattern (for directories)
        if path.startswith(pattern) or path_lower.startswith(pattern.lower()):
            return True
    
    return False

def get_ignore_patterns() -> Set[str]:
    """Legacy function name for compatibility"""
    return get_comprehensive_ignore_patterns()