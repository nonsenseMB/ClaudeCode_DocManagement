#!/usr/bin/env python3
"""
Intelligent Documentation System for Python Projects
Automatically analyzes, indexes and documents code with semantic search capabilities
"""

import ast
import os
import json
import hashlib
import logging
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from tqdm import tqdm
import click
from colorama import init, Fore, Style
from tabulate import tabulate

# Initialize colorama for cross-platform colored output
init()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CodeElement:
    """Represents a code element (function, class, route, model)"""
    name: str
    type: str  # function, class, api_route, model
    file_path: str
    line_number: int
    docstring: Optional[str]
    complexity_score: int
    dependencies: List[str]
    decorators: List[str]
    signature: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class FileAnalysis:
    """Complete analysis of a Python file"""
    file_path: str
    purpose: str
    elements: List[CodeElement]
    imports: List[str]
    api_routes: List[Dict[str, Any]]
    database_models: List[Dict[str, Any]]
    content_hash: str
    last_analyzed: str
    breaking_changes: List[str]
    architecture_decisions: List[str]


class CodeAnalyzer:
    """AST-based code analyzer for Python files"""
    
    def __init__(self):
        self.framework_patterns = {
            'fastapi': ['@app.', '@router.'],
            'flask': ['@app.route', '@blueprint.route'],
            'django': ['path(', 'url(', 'models.Model'],
            'sqlalchemy': ['declarative_base', 'Column(', 'relationship('],
            'pydantic': ['BaseModel', 'Field(']
        }
    
    def analyze_file(self, file_path: str) -> Optional[FileAnalysis]:
        """Analyze a Python file and extract all relevant information"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Calculate content hash
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            # Parse AST
            tree = ast.parse(content)
            
            # Extract elements
            elements = self._extract_elements(tree, file_path)
            imports = self._extract_imports(tree)
            api_routes = self._detect_api_routes(content, tree)
            db_models = self._detect_database_models(tree)
            
            # Calculate file purpose
            purpose = self._infer_purpose(file_path, elements, api_routes, db_models)
            
            return FileAnalysis(
                file_path=file_path,
                purpose=purpose,
                elements=elements,
                imports=imports,
                api_routes=api_routes,
                database_models=db_models,
                content_hash=content_hash,
                last_analyzed=datetime.now().isoformat(),
                breaking_changes=[],
                architecture_decisions=[]
            )
            
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return None
    
    def _extract_elements(self, tree: ast.AST, file_path: str) -> List[CodeElement]:
        """Extract all code elements from AST"""
        elements = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                elements.append(self._analyze_function(node, file_path))
            elif isinstance(node, ast.ClassDef):
                elements.append(self._analyze_class(node, file_path))
        
        return elements
    
    def _analyze_function(self, node: ast.FunctionDef, file_path: str) -> CodeElement:
        """Analyze a function node"""
        complexity = self._calculate_complexity(node)
        dependencies = self._extract_dependencies(node)
        decorators = [self._decorator_to_string(d) for d in node.decorator_list]
        
        # Extract signature
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        signature = f"{node.name}({', '.join(args)})"
        
        return CodeElement(
            name=node.name,
            type='function',
            file_path=file_path,
            line_number=node.lineno,
            docstring=ast.get_docstring(node),
            complexity_score=complexity,
            dependencies=dependencies,
            decorators=decorators,
            signature=signature
        )
    
    def _analyze_class(self, node: ast.ClassDef, file_path: str) -> CodeElement:
        """Analyze a class node"""
        complexity = self._calculate_complexity(node)
        dependencies = self._extract_dependencies(node)
        decorators = [self._decorator_to_string(d) for d in node.decorator_list]
        
        # Extract base classes
        bases = [self._node_to_string(base) for base in node.bases]
        
        return CodeElement(
            name=node.name,
            type='class',
            file_path=file_path,
            line_number=node.lineno,
            docstring=ast.get_docstring(node),
            complexity_score=complexity,
            dependencies=dependencies,
            decorators=decorators,
            metadata={'bases': bases}
        )
    
    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity score"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity
    
    def _extract_dependencies(self, node: ast.AST) -> List[str]:
        """Extract function/method calls as dependencies"""
        dependencies = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    dependencies.add(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    dependencies.add(self._node_to_string(child.func))
        return list(dependencies)
    
    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract all imports from file"""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        return imports
    
    def _detect_api_routes(self, content: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Detect API routes in the file"""
        routes = []
        
        # Check for FastAPI/Flask decorators
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    decorator_str = self._decorator_to_string(decorator)
                    
                    # FastAPI patterns
                    if any(pattern in decorator_str for pattern in ['@app.', '@router.']):
                        route_info = self._parse_fastapi_route(decorator_str, node)
                        if route_info:
                            routes.append(route_info)
                    
                    # Flask patterns
                    elif '@app.route' in decorator_str or '@blueprint.route' in decorator_str:
                        route_info = self._parse_flask_route(decorator_str, node)
                        if route_info:
                            routes.append(route_info)
        
        return routes
    
    def _detect_database_models(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Detect database models in the file"""
        models = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check for SQLAlchemy/Django/Pydantic models
                for base in node.bases:
                    base_str = self._node_to_string(base)
                    
                    if 'Model' in base_str or 'Base' in base_str:
                        model_info = {
                            'name': node.name,
                            'type': self._identify_model_type(base_str),
                            'fields': self._extract_model_fields(node),
                            'line_number': node.lineno
                        }
                        models.append(model_info)
        
        return models
    
    def _parse_fastapi_route(self, decorator_str: str, node: ast.FunctionDef) -> Optional[Dict[str, Any]]:
        """Parse FastAPI route decorator"""
        import re
        
        # Extract HTTP method and path
        match = re.search(r'@(?:app|router)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', decorator_str)
        if match:
            return {
                'method': match.group(1).upper(),
                'path': match.group(2),
                'handler': node.name,
                'line_number': node.lineno,
                'docstring': ast.get_docstring(node)
            }
        return None
    
    def _parse_flask_route(self, decorator_str: str, node: ast.FunctionDef) -> Optional[Dict[str, Any]]:
        """Parse Flask route decorator"""
        import re
        
        # Extract path and methods
        match = re.search(r'@(?:app|blueprint)\.route\(["\']([^"\']+)["\']', decorator_str)
        if match:
            methods_match = re.search(r'methods=\[([^\]]+)\]', decorator_str)
            methods = ['GET']  # Default
            if methods_match:
                methods = [m.strip().strip('"\'') for m in methods_match.group(1).split(',')]
            
            return {
                'method': methods,
                'path': match.group(1),
                'handler': node.name,
                'line_number': node.lineno,
                'docstring': ast.get_docstring(node)
            }
        return None
    
    def _identify_model_type(self, base_str: str) -> str:
        """Identify the type of database model"""
        if 'django' in base_str.lower() or 'models.Model' in base_str:
            return 'django'
        elif 'sqlalchemy' in base_str.lower() or 'Base' in base_str:
            return 'sqlalchemy'
        elif 'pydantic' in base_str.lower() or 'BaseModel' in base_str:
            return 'pydantic'
        return 'unknown'
    
    def _extract_model_fields(self, node: ast.ClassDef) -> List[Dict[str, str]]:
        """Extract fields from a model class"""
        fields = []
        
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field_info = {
                    'name': item.target.id,
                    'type': self._node_to_string(item.annotation) if item.annotation else 'Any'
                }
                fields.append(field_info)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        field_info = {
                            'name': target.id,
                            'type': 'inferred'
                        }
                        fields.append(field_info)
        
        return fields
    
    def _infer_purpose(self, file_path: str, elements: List[CodeElement], 
                      api_routes: List[Dict], db_models: List[Dict]) -> str:
        """Infer the purpose of a file based on its contents"""
        file_name = Path(file_path).stem
        
        if api_routes:
            return f"API endpoint definitions with {len(api_routes)} routes"
        elif db_models:
            return f"Database models with {len(db_models)} model definitions"
        elif 'test_' in file_name or '_test' in file_name:
            return "Test suite for unit/integration testing"
        elif 'config' in file_name or 'settings' in file_name:
            return "Configuration and settings management"
        elif 'util' in file_name or 'helper' in file_name:
            return "Utility functions and helper methods"
        elif elements:
            class_count = sum(1 for e in elements if e.type == 'class')
            func_count = sum(1 for e in elements if e.type == 'function')
            return f"Module with {class_count} classes and {func_count} functions"
        else:
            return "Python module"
    
    def _decorator_to_string(self, decorator: ast.AST) -> str:
        """Convert decorator AST node to string"""
        if isinstance(decorator, ast.Name):
            return f"@{decorator.id}"
        elif isinstance(decorator, ast.Attribute):
            return f"@{self._node_to_string(decorator)}"
        elif isinstance(decorator, ast.Call):
            return f"@{self._node_to_string(decorator)}"
        return "@unknown"
    
    def _node_to_string(self, node: ast.AST) -> str:
        """Convert AST node to string representation"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._node_to_string(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            func_str = self._node_to_string(node.func)
            args = ', '.join(self._node_to_string(arg) for arg in node.args)
            return f"{func_str}({args})"
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Str):
            return repr(node.s)
        return "unknown"


class LLMAnalyzer:
    """LLM-based code analyzer for high-level insights"""
    
    def __init__(self, model: str = "codellama:7b"):
        self.model = model
        self.ollama_available = self._check_ollama()
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is available"""
        try:
            import ollama
            # Test connection
            ollama.list()
            return True
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False
    
    def analyze_with_llm(self, file_analysis: FileAnalysis, content: str) -> FileAnalysis:
        """Enhance file analysis with LLM insights"""
        if not self.ollama_available:
            return self._fallback_analysis(file_analysis)
        
        try:
            import ollama
            
            # Prepare structured prompt
            prompt = self._create_analysis_prompt(file_analysis, content)
            
            # Get LLM response
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={'temperature': 0.3}
            )
            
            # Parse response
            insights = self._parse_llm_response(response['response'])
            
            # Update file analysis
            file_analysis.breaking_changes = insights.get('breaking_changes', [])
            file_analysis.architecture_decisions = insights.get('architecture_decisions', [])
            
            # Refine purpose if LLM provides better description
            if insights.get('purpose'):
                file_analysis.purpose = insights['purpose']
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return self._fallback_analysis(file_analysis)
        
        return file_analysis
    
    def _create_analysis_prompt(self, file_analysis: FileAnalysis, content: str) -> str:
        """Create structured prompt for LLM analysis"""
        # Limit content to avoid token limits
        content_preview = content[:3000] if len(content) > 3000 else content
        
        prompt = f"""Analyze this Python file and provide insights:

File: {file_analysis.file_path}
Elements: {len(file_analysis.elements)} functions/classes
API Routes: {len(file_analysis.api_routes)}
Models: {len(file_analysis.database_models)}

Code Preview:
```python
{content_preview}
```

Provide analysis in this exact format:

PURPOSE:
<One sentence describing the main purpose of this file>

ARCHITECTURE_DECISIONS:
- <Key architectural decision or pattern used>
- <Another architectural decision if applicable>

BREAKING_CHANGES:
- <Potential breaking change if this file is modified>
- <Another risk if applicable>

DEPENDENCIES:
- <Critical dependency this file relies on>
- <Another dependency if applicable>
"""
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse structured LLM response"""
        insights = {
            'purpose': '',
            'architecture_decisions': [],
            'breaking_changes': [],
            'dependencies': []
        }
        
        lines = response.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if 'PURPOSE:' in line:
                current_section = 'purpose'
            elif 'ARCHITECTURE_DECISIONS:' in line:
                current_section = 'architecture_decisions'
            elif 'BREAKING_CHANGES:' in line:
                current_section = 'breaking_changes'
            elif 'DEPENDENCIES:' in line:
                current_section = 'dependencies'
            elif line.startswith('- ') and current_section in ['architecture_decisions', 'breaking_changes', 'dependencies']:
                insights[current_section].append(line[2:])
            elif current_section == 'purpose' and line:
                insights['purpose'] = line
        
        return insights
    
    def _fallback_analysis(self, file_analysis: FileAnalysis) -> FileAnalysis:
        """Fallback analysis without LLM"""
        # Use heuristics for breaking changes
        breaking_changes = []
        
        # Check for critical patterns
        if any(route for route in file_analysis.api_routes):
            breaking_changes.append("Modifying API routes may break client applications")
        
        if any(model for model in file_analysis.database_models):
            breaking_changes.append("Changing database models requires migration")
        
        # High complexity functions are risky to modify
        complex_functions = [e for e in file_analysis.elements if e.complexity_score > 10]
        if complex_functions:
            breaking_changes.append(f"High complexity functions ({len(complex_functions)}) - changes may introduce bugs")
        
        file_analysis.breaking_changes = breaking_changes
        
        return file_analysis


class SemanticIndexer:
    """Semantic search indexer using ChromaDB and embeddings"""
    
    def __init__(self, db_path: str = "./vector_db", embedding_model: str = "microsoft/codebert-base"):
        self.db_path = db_path
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Initialize embedding model with fallback
        self.embedding_model_name = embedding_model
        self.embedding_model = self._init_embedding_model(embedding_model)
        
        # Create collections
        self.file_collection = self._get_or_create_collection("file_overviews")
        self.element_collection = self._get_or_create_collection("code_elements")
    
    def _init_embedding_model(self, model_name: str):
        """Initialize embedding model with fallback"""
        try:
            # Try to load the requested model (optimized for code)
            if "codebert" in model_name.lower():
                # CodeBERT is better for code understanding
                logger.info(f"Loading code-optimized model: {model_name}")
                return SentenceTransformer(model_name)
            else:
                return SentenceTransformer(model_name)
        except Exception as e:
            logger.warning(f"Could not load {model_name}: {e}")
            # Fallback to a smaller, reliable model
            fallback_model = 'all-MiniLM-L6-v2'
            logger.info(f"Falling back to {fallback_model}")
            return SentenceTransformer(fallback_model)
    
    def _get_or_create_collection(self, name: str):
        """Get or create a ChromaDB collection"""
        try:
            return self.client.get_collection(name)
        except:
            return self.client.create_collection(
                name=name,
                embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
            )
    
    def index_file(self, file_analysis: FileAnalysis):
        """Index a file and its elements"""
        # Index file overview
        file_doc = {
            'id': file_analysis.file_path,
            'text': f"{file_analysis.purpose}\n{' '.join(file_analysis.imports)}",
            'metadata': {
                'file_path': file_analysis.file_path,
                'purpose': file_analysis.purpose,
                'api_routes': len(file_analysis.api_routes),
                'models': len(file_analysis.database_models),
                'last_analyzed': file_analysis.last_analyzed
            }
        }
        
        self.file_collection.upsert(
            ids=[file_doc['id']],
            documents=[file_doc['text']],
            metadatas=[file_doc['metadata']]
        )
        
        # Index individual elements
        for element in file_analysis.elements:
            self._index_element(element)
    
    def _index_element(self, element: CodeElement):
        """Index a single code element"""
        # Create searchable text
        text_parts = [
            f"{element.type} {element.name}",
            element.docstring or "",
            ' '.join(element.dependencies),
            ' '.join(element.decorators)
        ]
        text = ' '.join(text_parts)
        
        element_id = f"{element.file_path}::{element.name}::{element.line_number}"
        
        self.element_collection.upsert(
            ids=[element_id],
            documents=[text],
            metadatas=[{
                'name': element.name,
                'type': element.type,
                'file_path': element.file_path,
                'line_number': element.line_number,
                'complexity': element.complexity_score,
                'has_docstring': bool(element.docstring)
            }]
        )
    
    def search(self, query: str, intent: str = "general", 
              filter_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Semantic search with intent-based filtering"""
        
        # Enhance query based on intent
        enhanced_query = self._enhance_query(query, intent)
        
        # Prepare filters
        where_clause = {}
        if filter_type:
            where_clause['type'] = filter_type
        
        # Search in appropriate collection
        if intent in ['find_file', 'understand_architecture']:
            results = self.file_collection.query(
                query_texts=[enhanced_query],
                n_results=limit,
                where=where_clause if where_clause else None
            )
        else:
            results = self.element_collection.query(
                query_texts=[enhanced_query],
                n_results=limit,
                where=where_clause if where_clause else None
            )
        
        # Format results
        formatted_results = []
        if results['ids'] and results['ids'][0]:
            for i, id_ in enumerate(results['ids'][0]):
                formatted_results.append({
                    'id': id_,
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else 0,
                    'document': results['documents'][0][i] if results['documents'] else ''
                })
        
        return formatted_results
    
    def _enhance_query(self, query: str, intent: str) -> str:
        """Enhance query based on search intent"""
        intent_prefixes = {
            'find_similar': f"similar implementation code function {query}",
            'understand_dependencies': f"dependencies imports uses {query}",
            'check_patterns': f"pattern architecture design {query}",
            'find_file': f"file module purpose {query}",
            'understand_architecture': f"architecture design pattern structure {query}"
        }
        return intent_prefixes.get(intent, query)
    
    def find_similar_code(self, description: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar code implementations"""
        return self.search(description, intent='find_similar', limit=limit)
    
    def get_dependencies(self, target: str) -> List[Dict[str, Any]]:
        """Find all code that depends on target"""
        # Search for elements that mention the target
        results = self.search(target, intent='understand_dependencies')
        
        # Filter to only those that actually depend on target
        dependencies = []
        for result in results:
            if target in result.get('document', ''):
                dependencies.append(result)
        
        return dependencies


class DocumentationSystem:
    """Main documentation system orchestrator"""
    
    def __init__(self, project_root: str = ".", docs_dir: str = "docs", 
                 llm_model: str = "codellama:7b", 
                 embedding_model: str = "microsoft/codebert-base",
                 vector_db_dir: str = "vector_db"):
        self.project_root = Path(project_root).resolve()
        self.docs_dir = self.project_root / docs_dir
        self.metadata_file = self.docs_dir / "file_metadata.json"
        self.vector_db_dir = self.project_root / vector_db_dir
        
        # Initialize components
        self.code_analyzer = CodeAnalyzer()
        
        # Import JS analyzer if needed
        try:
            from autodoc.core.js_analyzer import JavaScriptAnalyzer
            self.js_analyzer = JavaScriptAnalyzer()
        except ImportError:
            self.js_analyzer = None
            logger.warning("JavaScript analyzer not available")
        
        self.llm_analyzer = LLMAnalyzer(llm_model)
        self.indexer = SemanticIndexer(
            str(self.vector_db_dir),
            embedding_model=embedding_model
        )
        
        # File watcher
        self.observer = None
        self.file_handler = None
        
        # Create directories
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        (self.docs_dir / "files").mkdir(exist_ok=True)
        (self.docs_dir / "generated").mkdir(exist_ok=True)
        
        # Load metadata
        self.metadata = self._load_metadata()
        
        # Ignored patterns
        self.ignored_patterns = {
            '__pycache__', '.pytest_cache', '.git', 'venv', '.venv', 
            'node_modules', '__init__.py', 'migrations', '.pyc'
        }
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load file metadata from disk"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_metadata(self):
        """Save file metadata to disk"""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def should_process_file(self, file_path: str) -> bool:
        """Check if file should be processed"""
        path = Path(file_path)
        
        # Check if it's a supported file type
        supported_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx'}
        if path.suffix not in supported_extensions:
            return False
        
        # Check ignored patterns
        from autodoc.utils import should_ignore_path, get_comprehensive_ignore_patterns
        ignore_patterns = get_comprehensive_ignore_patterns()
        
        # Check full path and each component
        for part in path.parts:
            if should_ignore_path(part, ignore_patterns):
                return False
        
        # Check if file has changed
        if str(path) in self.metadata:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            current_hash = hashlib.md5(content.encode()).hexdigest()
            
            if self.metadata[str(path)].get('content_hash') == current_hash:
                return False
        
        return True
    
    def process_file(self, file_path: str) -> Optional[FileAnalysis]:
        """Process a single code file (Python or JavaScript)"""
        if not self.should_process_file(file_path):
            logger.info(f"Skipping {file_path} (unchanged or ignored)")
            return None
        
        logger.info(f"Processing {file_path}")
        
        # Determine file type and analyze accordingly
        path = Path(file_path)
        
        if path.suffix == '.py':
            # Python analysis
            analysis = self.code_analyzer.analyze_file(file_path)
        elif path.suffix in ['.js', '.jsx', '.ts', '.tsx'] and self.js_analyzer:
            # JavaScript/TypeScript analysis
            js_analysis = self.js_analyzer.analyze_file(file_path)
            if js_analysis:
                # Convert to common FileAnalysis format
                analysis = self._convert_js_to_common_analysis(js_analysis)
            else:
                return None
        else:
            logger.warning(f"Unsupported file type: {file_path}")
            return None
        
        if not analysis:
            return None
        
        # Enhance with LLM if available
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        analysis = self.llm_analyzer.analyze_with_llm(analysis, content)
        
        # Index for semantic search
        self.indexer.index_file(analysis)
        
        # Generate documentation
        self._generate_documentation(analysis)
        
        # Update metadata
        self.metadata[file_path] = {
            'content_hash': analysis.content_hash,
            'last_analyzed': analysis.last_analyzed,
            'elements_count': len(analysis.elements),
            'purpose': analysis.purpose
        }
        self._save_metadata()
        
        return analysis
    
    def _generate_documentation(self, analysis: FileAnalysis):
        """Generate markdown documentation for a file"""
        relative_path = Path(analysis.file_path).relative_to(self.project_root)
        doc_path = self.docs_dir / "files" / f"{relative_path.stem}.md"
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if manual content exists
        manual_content = ""
        if doc_path.exists():
            with open(doc_path, 'r') as f:
                content = f.read()
                # Extract manual content between markers
                if "<!-- manual_context_start -->" in content:
                    start = content.index("<!-- manual_context_start -->")
                    end = content.index("<!-- manual_context_end -->") if "<!-- manual_context_end -->" in content else len(content)
                    manual_content = content[start:end + len("<!-- manual_context_end -->")]
        
        # Generate new documentation
        doc = self._create_documentation_template(analysis, manual_content)
        
        with open(doc_path, 'w') as f:
            f.write(doc)
        
        logger.info(f"Documentation generated: {doc_path}")
    
    def _create_documentation_template(self, analysis: FileAnalysis, manual_content: str = "") -> str:
        """Create markdown documentation template"""
        doc = f"""# {Path(analysis.file_path).name}

## 🎯 Purpose
{analysis.purpose}

## 📍 Location
`{analysis.file_path}`

## ⏰ Last Updated
{analysis.last_analyzed}
"""
        
        # Breaking changes
        if analysis.breaking_changes:
            doc += "\n## ⚠️ Breaking Change Warnings\n"
            for warning in analysis.breaking_changes:
                doc += f"- {warning}\n"
        
        # Architecture decisions
        if analysis.architecture_decisions:
            doc += "\n## 🏗️ Architecture Decisions\n"
            for decision in analysis.architecture_decisions:
                doc += f"- {decision}\n"
        
        # Manual context section
        if not manual_content:
            manual_content = """<!-- manual_context_start -->
*Add developer context, design decisions, and important notes here*
<!-- manual_context_end -->"""
        
        doc += f"\n## 📝 Manual Context\n{manual_content}\n"
        
        # Code elements
        if analysis.elements:
            doc += "\n## 🧩 Code Elements\n\n"
            
            # Group by type
            functions = [e for e in analysis.elements if e.type == 'function']
            classes = [e for e in analysis.elements if e.type == 'class']
            
            if functions:
                doc += "### Functions\n"
                for func in sorted(functions, key=lambda x: x.complexity_score, reverse=True):
                    complexity_icon = self._get_complexity_icon(func.complexity_score)
                    doc_icon = "📖" if func.docstring else "❌"
                    doc += f"- `{func.signature or func.name}` {complexity_icon} {doc_icon} (line {func.line_number})\n"
                    if func.docstring:
                        doc += f"  - {func.docstring.split(chr(10))[0][:80]}...\n"
            
            if classes:
                doc += "\n### Classes\n"
                for cls in sorted(classes, key=lambda x: x.complexity_score, reverse=True):
                    complexity_icon = self._get_complexity_icon(cls.complexity_score)
                    doc_icon = "📖" if cls.docstring else "❌"
                    doc += f"- `{cls.name}` {complexity_icon} {doc_icon} (line {cls.line_number})\n"
                    if cls.metadata and cls.metadata.get('bases'):
                        doc += f"  - Inherits: {', '.join(cls.metadata['bases'])}\n"
        
        # API Routes
        if analysis.api_routes:
            doc += "\n## 🌐 API Routes\n"
            for route in analysis.api_routes:
                methods = route['method'] if isinstance(route['method'], list) else [route['method']]
                for method in methods:
                    doc += f"- `{method} {route['path']}` → `{route['handler']}()` (line {route['line_number']})\n"
        
        # Database Models
        if analysis.database_models:
            doc += "\n## 🗄️ Database Models\n"
            for model in analysis.database_models:
                doc += f"- `{model['name']}` ({model['type']}) - {len(model['fields'])} fields\n"
                for field in model['fields'][:5]:  # Show first 5 fields
                    doc += f"  - {field['name']}: {field['type']}\n"
                if len(model['fields']) > 5:
                    doc += f"  - ... and {len(model['fields']) - 5} more fields\n"
        
        # Dependencies
        if analysis.imports:
            doc += "\n## 📦 Dependencies\n"
            external_imports = [imp for imp in analysis.imports if not imp.startswith('.')]
            internal_imports = [imp for imp in analysis.imports if imp.startswith('.')]
            
            if external_imports:
                doc += "### External\n"
                for imp in sorted(set(external_imports))[:10]:
                    doc += f"- {imp}\n"
            
            if internal_imports:
                doc += "### Internal\n"
                for imp in sorted(set(internal_imports))[:10]:
                    doc += f"- {imp}\n"
        
        return doc
    
    def _get_complexity_icon(self, score: int) -> str:
        """Get complexity indicator icon"""
        if score <= 5:
            return "🟢"  # Low complexity
        elif score <= 10:
            return "🟡"  # Medium complexity
        else:
            return "🔴"  # High complexity
    
    def process_project(self, directories: List[str], parallel: bool = True):
        """Process entire project"""
        print(f"\n{Fore.CYAN}🔍 Scanning project for Python files...{Style.RESET_ALL}")
        
        # Collect all Python files
        python_files = []
        for directory in directories:
            dir_path = self.project_root / directory
            if dir_path.exists():
                for file_path in dir_path.rglob("*.py"):
                    if self.should_process_file(str(file_path)):
                        python_files.append(str(file_path))
        
        if not python_files:
            print(f"{Fore.YELLOW}No Python files to process.{Style.RESET_ALL}")
            return
        
        print(f"{Fore.GREEN}Found {len(python_files)} files to process{Style.RESET_ALL}")
        
        # Process files
        if parallel and len(python_files) > 1:
            self._process_parallel(python_files)
        else:
            self._process_sequential(python_files)
        
        # Generate project overview
        self._generate_project_overview()
        
        print(f"\n{Fore.GREEN}✅ Documentation generation complete!{Style.RESET_ALL}")
        print(f"📁 Documentation available in: {self.docs_dir}")
    
    def _process_sequential(self, files: List[str]):
        """Process files sequentially"""
        for file_path in tqdm(files, desc="Processing files"):
            try:
                self.process_file(file_path)
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
    
    def _process_parallel(self, files: List[str], max_workers: int = 4):
        """Process files in parallel"""
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.process_file, f): f for f in files}
            
            for future in tqdm(as_completed(futures), total=len(files), desc="Processing files"):
                file_path = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
    
    def _generate_project_overview(self):
        """Generate project-wide overview documentation"""
        overview_path = self.docs_dir / "PROJECT_OVERVIEW.md"
        
        # Collect statistics
        total_files = len(self.metadata)
        total_elements = sum(m.get('elements_count', 0) for m in self.metadata.values())
        
        # Get all API routes and models from indexed data
        api_routes = []
        db_models = []
        
        for file_path, meta in self.metadata.items():
            # Read the generated documentation to extract routes and models
            relative_path = Path(file_path).relative_to(self.project_root)
            doc_path = self.docs_dir / "files" / f"{relative_path.stem}.md"
            
            if doc_path.exists():
                with open(doc_path, 'r') as f:
                    content = f.read()
                    if "## 🌐 API Routes" in content:
                        api_routes.append(file_path)
                    if "## 🗄️ Database Models" in content:
                        db_models.append(file_path)
        
        # Generate overview
        overview = f"""# 📚 Project Documentation Overview

## 📊 Statistics
- **Total Files Analyzed**: {total_files}
- **Total Code Elements**: {total_elements}
- **Files with API Routes**: {len(api_routes)}
- **Files with Database Models**: {len(db_models)}
- **Last Updated**: {datetime.now().isoformat()}

## 📁 File Index

| File | Purpose | Elements | Status |
|------|---------|----------|--------|
"""
        
        # Add file entries
        for file_path, meta in sorted(self.metadata.items()):
            relative_path = Path(file_path).relative_to(self.project_root)
            purpose = meta.get('purpose', 'Unknown')[:50]
            elements = meta.get('elements_count', 0)
            status = "✅" if elements > 0 else "⚠️"
            
            doc_link = f"files/{relative_path.stem}.md"
            overview += f"| [{relative_path}]({doc_link}) | {purpose}... | {elements} | {status} |\n"
        
        # Add quick access sections
        if api_routes:
            overview += "\n## 🌐 API Endpoints\n"
            for file_path in api_routes[:10]:
                relative_path = Path(file_path).relative_to(self.project_root)
                overview += f"- [{relative_path}](files/{relative_path.stem}.md)\n"
        
        if db_models:
            overview += "\n## 🗄️ Database Models\n"
            for file_path in db_models[:10]:
                relative_path = Path(file_path).relative_to(self.project_root)
                overview += f"- [{relative_path}](files/{relative_path.stem}.md)\n"
        
        # Add search tips
        overview += """
## 🔍 Search Tips

Use the MCP server tools to search this documentation:
- `search_docs "user authentication"` - Find relevant documentation
- `find_similar_code "validate input"` - Find similar implementations
- `check_dependencies "FastAPI"` - Find all code using a dependency
- `list_api_routes` - List all API endpoints
- `list_database_models` - List all database models

## 🤝 Contributing

When adding new code:
1. Check existing patterns with `suggest_patterns`
2. Search for similar implementations first
3. Follow established architecture decisions
4. Update manual context sections in documentation
"""
        
        with open(overview_path, 'w') as f:
            f.write(overview)
        
        print(f"{Fore.GREEN}📄 Project overview generated: {overview_path}{Style.RESET_ALL}")
    
    def start_file_watcher(self, directories: List[str]):
        """Start watching files for changes"""
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        
        class ChangeHandler(FileSystemEventHandler):
            def __init__(self, doc_system):
                self.doc_system = doc_system
                self.pending_files = set()
                self.last_event_time = {}
            
            def should_process(self, file_path: str) -> bool:
                """Check if file should be processed with debouncing"""
                current_time = time.time()
                last_time = self.last_event_time.get(file_path, 0)
                
                # Debounce: wait 2 seconds after last event
                if current_time - last_time < 2:
                    return False
                
                self.last_event_time[file_path] = current_time
                return True
            
            def on_modified(self, event):
                if not event.is_directory and event.src_path.endswith('.py'):
                    if self.should_process(event.src_path):
                        logger.info(f"File changed: {event.src_path}")
                        self.doc_system.process_file(event.src_path)
        
        self.file_handler = ChangeHandler(self)
        self.observer = Observer()
        
        for directory in directories:
            dir_path = self.project_root / directory
            if dir_path.exists():
                self.observer.schedule(self.file_handler, str(dir_path), recursive=True)
        
        self.observer.start()
        print(f"{Fore.CYAN}👁️ File watcher started for: {', '.join(directories)}{Style.RESET_ALL}")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
            print(f"\n{Fore.YELLOW}File watcher stopped.{Style.RESET_ALL}")
        
        self.observer.join()
    
    def _convert_js_to_common_analysis(self, js_analysis) -> FileAnalysis:
        """Convert JavaScript analysis to common FileAnalysis format"""
        
        # Convert JS elements to common CodeElement format
        elements = []
        for js_elem in js_analysis.elements:
            elements.append(CodeElement(
                name=js_elem.name,
                type=js_elem.type,
                file_path=js_elem.file_path,
                line_number=js_elem.line_number,
                docstring=js_elem.docstring,
                complexity_score=js_elem.complexity_score,
                dependencies=js_elem.dependencies,
                decorators=[],  # JS doesn't have decorators like Python
                signature=js_elem.signature,
                metadata=js_elem.metadata
            ))
        
        # Convert React components to API routes format for consistency
        api_routes = []
        for comp in js_analysis.react_components:
            api_routes.append({
                'method': 'COMPONENT',
                'path': f"/{comp['name']}",
                'handler': comp['name'],
                'line_number': 0,
                'docstring': f"{comp['type']} React component"
            })
        
        # Add actual API calls
        for api in js_analysis.api_calls:
            api_routes.append({
                'method': api.get('type', 'API').upper(),
                'path': api.get('url', api.get('path', '/')),
                'handler': 'api_call',
                'line_number': 0,
                'docstring': None
            })
        
        return FileAnalysis(
            file_path=js_analysis.file_path,
            purpose=js_analysis.purpose,
            elements=elements,
            imports=js_analysis.imports,
            api_routes=api_routes,
            database_models=[],  # JS typically doesn't have DB models inline
            content_hash=js_analysis.content_hash,
            last_analyzed=js_analysis.last_analyzed,
            breaking_changes=[],
            architecture_decisions=[f"Framework: {js_analysis.framework}"]
        )


@click.command()
@click.option('--project-root', default='.', help='Project root directory')
@click.option('--docs-dir', default='docs', help='Documentation output directory')
@click.option('--llm-model', default='codellama:7b', help='LLM model for analysis')
@click.option('--directories', '-d', multiple=True, default=['src', 'app'], help='Directories to analyze')
@click.option('--watch', is_flag=True, help='Watch files for changes')
@click.option('--parallel', is_flag=True, default=True, help='Process files in parallel')
def main(project_root, docs_dir, llm_model, directories, watch, parallel):
    """Intelligent Documentation System for Python Projects"""
    
    print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🤖 Intelligent Documentation System{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}\n")
    
    # Initialize system
    doc_system = DocumentationSystem(
        project_root=project_root,
        docs_dir=docs_dir,
        llm_model=llm_model
    )
    
    # Process project
    doc_system.process_project(list(directories), parallel=parallel)
    
    # Start watcher if requested
    if watch:
        doc_system.start_file_watcher(list(directories))


if __name__ == "__main__":
    main()