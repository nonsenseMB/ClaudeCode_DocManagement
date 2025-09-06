#!/usr/bin/env python3
"""
MCP Server for Intelligent Documentation System
Provides semantic search and code analysis tools via MCP protocol
"""

import sys
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp.server import Server, Tool
from mcp.server.stdio import stdio_server
from autodoc.core import (
    DocumentationSystem,
    CodeAnalyzer,
    SemanticIndexer,
    FileAnalysis
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentationMCPServer:
    """MCP Server for documentation system"""
    
    def __init__(self, project_root: str = ".", docs_dir: str = "docs"):
        self.project_root = Path(project_root).resolve()
        self.docs_dir = self.project_root / docs_dir
        
        # Initialize documentation system
        self.doc_system = DocumentationSystem(
            project_root=str(self.project_root),
            docs_dir=docs_dir
        )
        
        # Load cached metadata
        self.metadata = self.doc_system.metadata
        
        # Quick access caches
        self._api_routes_cache = None
        self._db_models_cache = None
        self._last_cache_update = None
    
    def _update_caches(self):
        """Update internal caches from documentation"""
        current_time = datetime.now()
        
        # Update every 5 minutes
        if self._last_cache_update and (current_time - self._last_cache_update).seconds < 300:
            return
        
        self._api_routes_cache = []
        self._db_models_cache = []
        
        # Scan documentation files for routes and models
        for doc_file in (self.docs_dir / "files").glob("*.md"):
            with open(doc_file, 'r') as f:
                content = f.read()
                
                # Extract API routes
                if "## 🌐 API Routes" in content:
                    lines = content.split('\n')
                    in_routes = False
                    for line in lines:
                        if "## 🌐 API Routes" in line:
                            in_routes = True
                        elif in_routes and line.startswith("## "):
                            break
                        elif in_routes and line.strip().startswith("- `"):
                            # Parse route line
                            route_info = self._parse_route_line(line)
                            if route_info:
                                self._api_routes_cache.append(route_info)
                
                # Extract database models  
                if "## 🗄️ Database Models" in content:
                    lines = content.split('\n')
                    in_models = False
                    for line in lines:
                        if "## 🗄️ Database Models" in line:
                            in_models = True
                        elif in_models and line.startswith("## "):
                            break
                        elif in_models and line.strip().startswith("- `"):
                            # Parse model line
                            model_info = self._parse_model_line(line, doc_file.stem)
                            if model_info:
                                self._db_models_cache.append(model_info)
        
        self._last_cache_update = current_time
    
    def _parse_route_line(self, line: str) -> Optional[Dict[str, str]]:
        """Parse an API route line from documentation"""
        import re
        match = re.search(r'`([A-Z]+)\s+([^`]+)`\s+→\s+`([^`]+)`.*line\s+(\d+)', line)
        if match:
            return {
                'method': match.group(1),
                'path': match.group(2),
                'handler': match.group(3),
                'line': match.group(4)
            }
        return None
    
    def _parse_model_line(self, line: str, file_stem: str) -> Optional[Dict[str, str]]:
        """Parse a database model line from documentation"""
        import re
        match = re.search(r'`([^`]+)`\s+\(([^)]+)\)\s+-\s+(\d+)\s+fields', line)
        if match:
            return {
                'name': match.group(1),
                'type': match.group(2),
                'fields': match.group(3),
                'file': file_stem
            }
        return None
    
    async def search_docs(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Search documentation using semantic search
        
        Args:
            query: Search query
            limit: Maximum number of results
        
        Returns:
            Search results with relevance scores
        """
        try:
            results = self.doc_system.indexer.search(
                query=query,
                intent="general",
                limit=limit
            )
            
            # Format results for display
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'file': result['metadata'].get('file_path', 'Unknown'),
                    'type': result['metadata'].get('type', 'file'),
                    'name': result['metadata'].get('name', ''),
                    'line': result['metadata'].get('line_number', 0),
                    'relevance': 1.0 - result['distance'],  # Convert distance to relevance
                    'snippet': result['document'][:200] if result['document'] else ''
                })
            
            return {
                'status': 'success',
                'query': query,
                'results_count': len(formatted_results),
                'results': formatted_results
            }
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'results': []
            }
    
    async def find_similar_code(self, description: str, limit: int = 5) -> Dict[str, Any]:
        """
        Find similar code implementations
        
        Args:
            description: Description of functionality to find
            limit: Maximum number of results
        
        Returns:
            Similar code elements with locations
        """
        try:
            results = self.doc_system.indexer.find_similar_code(
                description=description,
                limit=limit
            )
            
            # Format results
            similar_code = []
            for result in results:
                meta = result['metadata']
                similar_code.append({
                    'name': meta.get('name', 'Unknown'),
                    'type': meta.get('type', 'unknown'),
                    'file': meta.get('file_path', ''),
                    'line': meta.get('line_number', 0),
                    'complexity': meta.get('complexity', 0),
                    'has_docs': meta.get('has_docstring', False),
                    'similarity': 1.0 - result['distance']
                })
            
            return {
                'status': 'success',
                'description': description,
                'found': len(similar_code),
                'similar_implementations': similar_code
            }
            
        except Exception as e:
            logger.error(f"Find similar code error: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'similar_implementations': []
            }
    
    async def check_dependencies(self, target: str) -> Dict[str, Any]:
        """
        Check what code depends on a target module/function
        
        Args:
            target: Name of module, function, or class to check
        
        Returns:
            List of dependencies and their locations
        """
        try:
            results = self.doc_system.indexer.get_dependencies(target)
            
            # Group dependencies by file
            dependencies_by_file = {}
            for result in results:
                meta = result['metadata']
                file_path = meta.get('file_path', 'Unknown')
                
                if file_path not in dependencies_by_file:
                    dependencies_by_file[file_path] = []
                
                dependencies_by_file[file_path].append({
                    'element': meta.get('name', ''),
                    'type': meta.get('type', ''),
                    'line': meta.get('line_number', 0)
                })
            
            return {
                'status': 'success',
                'target': target,
                'files_affected': len(dependencies_by_file),
                'dependencies': dependencies_by_file
            }
            
        except Exception as e:
            logger.error(f"Check dependencies error: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'dependencies': {}
            }
    
    async def get_file_context(self, file_path: str) -> Dict[str, Any]:
        """
        Get complete documentation for a file
        
        Args:
            file_path: Path to the Python file
        
        Returns:
            Complete file documentation and analysis
        """
        try:
            # Check if documentation exists
            relative_path = Path(file_path).relative_to(self.project_root)
            doc_path = self.docs_dir / "files" / f"{relative_path.stem}.md"
            
            if not doc_path.exists():
                # Generate documentation on demand
                analysis = self.doc_system.process_file(file_path)
                if not analysis:
                    return {
                        'status': 'error',
                        'error': 'Could not analyze file',
                        'file_path': file_path
                    }
            
            # Read documentation
            with open(doc_path, 'r') as f:
                documentation = f.read()
            
            # Get metadata
            metadata = self.doc_system.metadata.get(str(file_path), {})
            
            return {
                'status': 'success',
                'file_path': file_path,
                'purpose': metadata.get('purpose', 'Unknown'),
                'elements_count': metadata.get('elements_count', 0),
                'last_analyzed': metadata.get('last_analyzed', ''),
                'documentation': documentation
            }
            
        except Exception as e:
            logger.error(f"Get file context error: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'file_path': file_path
            }
    
    async def list_api_routes(self) -> Dict[str, Any]:
        """
        List all API routes in the project
        
        Returns:
            All API endpoints grouped by file
        """
        try:
            self._update_caches()
            
            # Group routes by file
            routes_by_file = {}
            for route in self._api_routes_cache:
                file_key = route.get('file', 'unknown')
                if file_key not in routes_by_file:
                    routes_by_file[file_key] = []
                routes_by_file[file_key].append(route)
            
            # Count statistics
            total_routes = len(self._api_routes_cache)
            methods_count = {}
            for route in self._api_routes_cache:
                method = route.get('method', 'UNKNOWN')
                methods_count[method] = methods_count.get(method, 0) + 1
            
            return {
                'status': 'success',
                'total_routes': total_routes,
                'methods': methods_count,
                'routes_by_file': routes_by_file
            }
            
        except Exception as e:
            logger.error(f"List API routes error: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'routes_by_file': {}
            }
    
    async def list_database_models(self) -> Dict[str, Any]:
        """
        List all database models in the project
        
        Returns:
            All database models with their types
        """
        try:
            self._update_caches()
            
            # Group models by type
            models_by_type = {}
            for model in self._db_models_cache:
                model_type = model.get('type', 'unknown')
                if model_type not in models_by_type:
                    models_by_type[model_type] = []
                models_by_type[model_type].append(model)
            
            return {
                'status': 'success',
                'total_models': len(self._db_models_cache),
                'models_by_type': models_by_type,
                'all_models': self._db_models_cache
            }
            
        except Exception as e:
            logger.error(f"List database models error: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'all_models': []
            }
    
    async def suggest_patterns(self, context: str) -> Dict[str, Any]:
        """
        Suggest existing patterns based on context
        
        Args:
            context: Description of what you want to implement
        
        Returns:
            Suggested patterns and examples from codebase
        """
        try:
            # Search for relevant patterns
            search_results = self.doc_system.indexer.search(
                query=context,
                intent="check_patterns",
                limit=10
            )
            
            # Extract patterns
            patterns = []
            seen_patterns = set()
            
            for result in search_results:
                meta = result['metadata']
                
                # Create pattern signature
                pattern_key = f"{meta.get('type', '')}:{meta.get('name', '')}"
                if pattern_key not in seen_patterns:
                    seen_patterns.add(pattern_key)
                    patterns.append({
                        'pattern': meta.get('name', ''),
                        'type': meta.get('type', ''),
                        'file': meta.get('file_path', ''),
                        'line': meta.get('line_number', 0),
                        'example': result['document'][:150] if result['document'] else ''
                    })
            
            # Get architecture decisions from metadata
            architecture_hints = []
            for file_path, meta in self.doc_system.metadata.items():
                if context.lower() in meta.get('purpose', '').lower():
                    architecture_hints.append({
                        'file': file_path,
                        'purpose': meta['purpose']
                    })
            
            return {
                'status': 'success',
                'context': context,
                'suggested_patterns': patterns[:5],
                'architecture_hints': architecture_hints[:3],
                'recommendation': self._generate_pattern_recommendation(patterns, context)
            }
            
        except Exception as e:
            logger.error(f"Suggest patterns error: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'suggested_patterns': []
            }
    
    def _generate_pattern_recommendation(self, patterns: List[Dict], context: str) -> str:
        """Generate recommendation based on found patterns"""
        if not patterns:
            return f"No existing patterns found for '{context}'. Consider creating a new pattern."
        
        pattern_types = set(p['type'] for p in patterns)
        
        if 'class' in pattern_types:
            return f"Found {len(patterns)} similar implementations. Consider extending existing classes or following the same structure."
        elif 'function' in pattern_types:
            return f"Found {len(patterns)} similar functions. Reuse existing utilities or follow the same naming conventions."
        else:
            return f"Found {len(patterns)} related patterns. Review these before implementing."
    
    async def analyze_complexity(self, threshold: int = 10) -> Dict[str, Any]:
        """
        Find complex code areas that need refactoring
        
        Args:
            threshold: Complexity score threshold
        
        Returns:
            List of complex code elements
        """
        try:
            # Search for all elements
            all_elements = self.doc_system.indexer.element_collection.get()
            
            # Filter by complexity
            complex_elements = []
            if all_elements and 'metadatas' in all_elements:
                for i, meta in enumerate(all_elements['metadatas']):
                    if meta.get('complexity', 0) >= threshold:
                        complex_elements.append({
                            'name': meta.get('name', ''),
                            'type': meta.get('type', ''),
                            'file': meta.get('file_path', ''),
                            'line': meta.get('line_number', 0),
                            'complexity': meta.get('complexity', 0),
                            'needs_refactoring': meta.get('complexity', 0) > 15
                        })
            
            # Sort by complexity
            complex_elements.sort(key=lambda x: x['complexity'], reverse=True)
            
            # Calculate statistics
            total_complex = len(complex_elements)
            critical_count = sum(1 for e in complex_elements if e['complexity'] > 20)
            high_count = sum(1 for e in complex_elements if 15 < e['complexity'] <= 20)
            medium_count = sum(1 for e in complex_elements if 10 <= e['complexity'] <= 15)
            
            return {
                'status': 'success',
                'threshold': threshold,
                'total_complex_elements': total_complex,
                'statistics': {
                    'critical': critical_count,
                    'high': high_count,
                    'medium': medium_count
                },
                'complex_elements': complex_elements[:20],  # Top 20 most complex
                'recommendations': self._generate_complexity_recommendations(complex_elements)
            }
            
        except Exception as e:
            logger.error(f"Analyze complexity error: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'complex_elements': []
            }
    
    def _generate_complexity_recommendations(self, complex_elements: List[Dict]) -> List[str]:
        """Generate refactoring recommendations"""
        recommendations = []
        
        critical = [e for e in complex_elements if e['complexity'] > 20]
        if critical:
            recommendations.append(f"⚠️ {len(critical)} critical complexity functions need immediate refactoring")
        
        high_complexity_files = {}
        for element in complex_elements:
            file_path = element['file']
            if file_path not in high_complexity_files:
                high_complexity_files[file_path] = 0
            high_complexity_files[file_path] += 1
        
        hotspot_files = [f for f, count in high_complexity_files.items() if count > 3]
        if hotspot_files:
            recommendations.append(f"📁 {len(hotspot_files)} files are complexity hotspots and need restructuring")
        
        functions = [e for e in complex_elements if e['type'] == 'function' and e['complexity'] > 15]
        if functions:
            recommendations.append(f"🔧 Consider breaking down {len(functions)} complex functions into smaller units")
        
        return recommendations


async def main():
    """Main entry point for MCP server"""
    logger.info("Starting Documentation MCP Server...")
    
    # Initialize server
    doc_server = DocumentationMCPServer(
        project_root=os.getenv("DOC_SYSTEM_PROJECT_ROOT", "."),
        docs_dir=os.getenv("DOC_SYSTEM_DOCS_DIR", "docs")
    )
    
    # Create MCP server
    server = Server("documentation-system")
    
    # Register tools
    @server.tool()
    async def search_docs(query: str, limit: int = 10) -> Dict[str, Any]:
        """Search documentation using semantic search"""
        return await doc_server.search_docs(query, limit)
    
    @server.tool()
    async def find_similar_code(description: str, limit: int = 5) -> Dict[str, Any]:
        """Find similar code implementations"""
        return await doc_server.find_similar_code(description, limit)
    
    @server.tool()
    async def check_dependencies(target: str) -> Dict[str, Any]:
        """Check what code depends on a target module/function"""
        return await doc_server.check_dependencies(target)
    
    @server.tool()
    async def get_file_context(file_path: str) -> Dict[str, Any]:
        """Get complete documentation for a file"""
        return await doc_server.get_file_context(file_path)
    
    @server.tool()
    async def list_api_routes() -> Dict[str, Any]:
        """List all API routes in the project"""
        return await doc_server.list_api_routes()
    
    @server.tool()
    async def list_database_models() -> Dict[str, Any]:
        """List all database models in the project"""
        return await doc_server.list_database_models()
    
    @server.tool()
    async def suggest_patterns(context: str) -> Dict[str, Any]:
        """Suggest existing patterns based on context"""
        return await doc_server.suggest_patterns(context)
    
    @server.tool()
    async def analyze_complexity(threshold: int = 10) -> Dict[str, Any]:
        """Find complex code areas that need refactoring"""
        return await doc_server.analyze_complexity(threshold)
    
    # Start server
    async with stdio_server() as (read_stream, write_stream):
        logger.info("MCP Server ready and listening...")
        await server.run(read_stream, write_stream)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())