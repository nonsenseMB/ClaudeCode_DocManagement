#!/usr/bin/env python3
"""
JavaScript/TypeScript Code Analyzer for AutoDoc
Analyzes JS/TS/JSX/TSX files for documentation
"""

import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class JSCodeElement:
    """Represents a JavaScript/TypeScript code element"""
    name: str
    type: str  # function, class, component, interface, type, const
    file_path: str
    line_number: int
    docstring: Optional[str]
    complexity_score: int
    dependencies: List[str]
    exports: bool
    signature: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass  
class JSFileAnalysis:
    """Complete analysis of a JavaScript/TypeScript file"""
    file_path: str
    purpose: str
    elements: List[JSCodeElement]
    imports: List[str]
    exports: List[str]
    react_components: List[Dict[str, Any]]
    api_calls: List[Dict[str, Any]]
    content_hash: str
    last_analyzed: str
    framework: str  # react, vue, angular, nodejs, vanilla


class JavaScriptAnalyzer:
    """Analyzer for JavaScript/TypeScript files using regex patterns"""
    
    def __init__(self):
        self.framework_patterns = {
            'react': ['import.*from.*react', 'React\\.', 'useState', 'useEffect', 'jsx'],
            'vue': ['<template>', '<script>', 'Vue\\.', 'export default.*{'],
            'angular': ['@Component', '@Injectable', 'import.*from.*@angular'],
            'express': ['express\\(\\)', 'app\\.get', 'app\\.post', 'router\\.'],
            'next': ['import.*from.*next', 'getServerSideProps', 'getStaticProps']
        }
        
    def analyze_file(self, file_path: str) -> Optional[JSFileAnalysis]:
        """Analyze a JavaScript/TypeScript file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Calculate content hash
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            # Detect file type
            is_typescript = file_path.endswith(('.ts', '.tsx'))
            is_jsx = file_path.endswith(('.jsx', '.tsx'))
            
            # Extract elements
            elements = self._extract_elements(content, file_path)
            imports = self._extract_imports(content)
            exports = self._extract_exports(content)
            react_components = self._detect_react_components(content) if is_jsx else []
            api_calls = self._detect_api_calls(content)
            framework = self._detect_framework(content, file_path)
            
            # Infer purpose
            purpose = self._infer_purpose(file_path, elements, react_components, api_calls, framework)
            
            return JSFileAnalysis(
                file_path=file_path,
                purpose=purpose,
                elements=elements,
                imports=imports,
                exports=exports,
                react_components=react_components,
                api_calls=api_calls,
                content_hash=content_hash,
                last_analyzed=datetime.now().isoformat(),
                framework=framework
            )
            
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return None
    
    def _extract_elements(self, content: str, file_path: str) -> List[JSCodeElement]:
        """Extract code elements from JavaScript/TypeScript"""
        elements = []
        lines = content.split('\n')
        
        # Function patterns
        function_patterns = [
            # Regular functions
            r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)',
            # Arrow functions
            r'^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>',
            # Method in object/class
            r'^\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{',
        ]
        
        # Class patterns
        class_pattern = r'^\s*(?:export\s+)?(?:default\s+)?class\s+(\w+)'
        
        # Interface/Type patterns (TypeScript)
        interface_pattern = r'^\s*(?:export\s+)?interface\s+(\w+)'
        type_pattern = r'^\s*(?:export\s+)?type\s+(\w+)'
        
        # React component patterns
        component_patterns = [
            r'^\s*(?:export\s+)?(?:default\s+)?function\s+([A-Z]\w+)',  # Functional component
            r'^\s*(?:export\s+)?const\s+([A-Z]\w+)\s*=',  # Const component
        ]
        
        for i, line in enumerate(lines, 1):
            # Check for functions
            for pattern in function_patterns:
                match = re.match(pattern, line)
                if match:
                    name = match.group(1)
                    is_export = 'export' in line
                    complexity = self._calculate_complexity(content, i)
                    
                    elements.append(JSCodeElement(
                        name=name,
                        type='function',
                        file_path=file_path,
                        line_number=i,
                        docstring=self._extract_jsdoc(lines, i-1),
                        complexity_score=complexity,
                        dependencies=self._extract_dependencies(content),
                        exports=is_export,
                        signature=line.strip()
                    ))
            
            # Check for classes
            match = re.match(class_pattern, line)
            if match:
                name = match.group(1)
                is_export = 'export' in line
                
                elements.append(JSCodeElement(
                    name=name,
                    type='class',
                    file_path=file_path,
                    line_number=i,
                    docstring=self._extract_jsdoc(lines, i-1),
                    complexity_score=self._calculate_complexity(content, i),
                    dependencies=self._extract_dependencies(content),
                    exports=is_export,
                    metadata={'extends': self._extract_extends(line)}
                ))
            
            # Check for interfaces (TypeScript)
            match = re.match(interface_pattern, line)
            if match:
                elements.append(JSCodeElement(
                    name=match.group(1),
                    type='interface',
                    file_path=file_path,
                    line_number=i,
                    docstring=self._extract_jsdoc(lines, i-1),
                    complexity_score=0,
                    dependencies=[],
                    exports='export' in line
                ))
            
            # Check for types (TypeScript)
            match = re.match(type_pattern, line)
            if match:
                elements.append(JSCodeElement(
                    name=match.group(1),
                    type='type',
                    file_path=file_path,
                    line_number=i,
                    docstring=self._extract_jsdoc(lines, i-1),
                    complexity_score=0,
                    dependencies=[],
                    exports='export' in line
                ))
            
            # Check for React components
            for pattern in component_patterns:
                match = re.match(pattern, line)
                if match:
                    name = match.group(1)
                    if name[0].isupper():  # React components start with uppercase
                        elements.append(JSCodeElement(
                            name=name,
                            type='component',
                            file_path=file_path,
                            line_number=i,
                            docstring=self._extract_jsdoc(lines, i-1),
                            complexity_score=self._calculate_complexity(content, i),
                            dependencies=self._extract_dependencies(content),
                            exports='export' in line,
                            metadata={'props': self._extract_props(content, name)}
                        ))
        
        return elements
    
    def _extract_imports(self, content: str) -> List[str]:
        """Extract all import statements"""
        imports = []
        
        # ES6 imports
        es6_imports = re.findall(r'import\s+(?:.*?)\s+from\s+[\'"]([^\'"]+)[\'"]', content)
        imports.extend(es6_imports)
        
        # CommonJS requires
        requires = re.findall(r'require\([\'"]([^\'"]+)[\'"]\)', content)
        imports.extend(requires)
        
        # Dynamic imports
        dynamic = re.findall(r'import\([\'"]([^\'"]+)[\'"]\)', content)
        imports.extend(dynamic)
        
        return list(set(imports))
    
    def _extract_exports(self, content: str) -> List[str]:
        """Extract all exports"""
        exports = []
        
        # Named exports
        named = re.findall(r'export\s+(?:const|let|var|function|class)\s+(\w+)', content)
        exports.extend(named)
        
        # Export statements
        export_statements = re.findall(r'export\s+\{([^}]+)\}', content)
        for statement in export_statements:
            exports.extend([s.strip() for s in statement.split(',')])
        
        # Default export
        if 'export default' in content:
            exports.append('default')
        
        return list(set(exports))
    
    def _detect_react_components(self, content: str) -> List[Dict[str, Any]]:
        """Detect React components in the file"""
        components = []
        
        # Function components
        func_components = re.findall(
            r'(?:export\s+)?(?:const|function)\s+([A-Z]\w+).*?(?:=>|\{)',
            content
        )
        
        for comp in func_components:
            components.append({
                'name': comp,
                'type': 'functional',
                'hooks': self._extract_hooks(content),
                'props': self._extract_props(content, comp)
            })
        
        # Class components
        class_components = re.findall(
            r'class\s+([A-Z]\w+)\s+extends\s+(?:React\.)?Component',
            content
        )
        
        for comp in class_components:
            components.append({
                'name': comp,
                'type': 'class',
                'lifecycle': self._extract_lifecycle_methods(content),
                'state': bool(re.search(r'this\.state', content))
            })
        
        return components
    
    def _detect_api_calls(self, content: str) -> List[Dict[str, Any]]:
        """Detect API calls in the file"""
        api_calls = []
        
        # Fetch calls
        fetch_calls = re.findall(r'fetch\([\'"`]([^\'"`)]+)[\'"`]', content)
        for url in fetch_calls:
            api_calls.append({'type': 'fetch', 'url': url})
        
        # Axios calls
        axios_calls = re.findall(r'axios\.(?:get|post|put|delete|patch)\([\'"`]([^\'"`)]+)[\'"`]', content)
        for url in axios_calls:
            api_calls.append({'type': 'axios', 'url': url})
        
        # Express routes (if server-side)
        express_routes = re.findall(r'app\.(?:get|post|put|delete|patch)\([\'"`]([^\'"`)]+)[\'"`]', content)
        for route in express_routes:
            api_calls.append({'type': 'express_route', 'path': route})
        
        return api_calls
    
    def _detect_framework(self, content: str, file_path: str) -> str:
        """Detect the JavaScript framework used"""
        for framework, patterns in self.framework_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return framework
        
        # Check file extensions for hints
        if file_path.endswith('.vue'):
            return 'vue'
        elif 'component' in file_path.lower():
            return 'react'  # Assume React for component files
        
        return 'vanilla'
    
    def _calculate_complexity(self, content: str, start_line: int) -> int:
        """Calculate cyclomatic complexity for JavaScript"""
        complexity = 1
        
        # Count decision points
        complexity += content.count('if ')
        complexity += content.count('else if')
        complexity += content.count('switch ')
        complexity += content.count('for ')
        complexity += content.count('while ')
        complexity += content.count('catch ')
        complexity += content.count(' ? ')  # Ternary operators
        complexity += content.count('&&')  # Logical AND
        complexity += content.count('||')  # Logical OR
        
        return min(complexity, 20)  # Cap at 20 for sanity
    
    def _extract_jsdoc(self, lines: List[str], comment_end_line: int) -> Optional[str]:
        """Extract JSDoc comment above a declaration"""
        if comment_end_line < 0:
            return None
        
        jsdoc_lines = []
        i = comment_end_line
        
        # Look for JSDoc comment ending
        if i >= 0 and '*/' in lines[i]:
            # Work backwards to find start
            while i >= 0:
                line = lines[i]
                jsdoc_lines.insert(0, line)
                if '/**' in line:
                    break
                i -= 1
            
            if jsdoc_lines and '/**' in jsdoc_lines[0]:
                # Clean up JSDoc
                jsdoc = '\n'.join(jsdoc_lines)
                jsdoc = re.sub(r'/\*\*|\*/|^\s*\*\s?', '', jsdoc, flags=re.MULTILINE)
                return jsdoc.strip()
        
        return None
    
    def _extract_dependencies(self, content: str) -> List[str]:
        """Extract function/method calls as dependencies"""
        deps = set()
        
        # Function calls
        calls = re.findall(r'(\w+)\s*\(', content)
        deps.update(calls)
        
        # Method calls
        methods = re.findall(r'\.(\w+)\s*\(', content)
        deps.update(methods)
        
        return list(deps)[:20]  # Limit to 20 most common
    
    def _extract_extends(self, line: str) -> Optional[str]:
        """Extract what a class extends"""
        match = re.search(r'extends\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_props(self, content: str, component_name: str) -> List[str]:
        """Extract props for a React component"""
        props = []
        
        # TypeScript props interface
        interface_match = re.search(
            rf'interface\s+{component_name}Props\s*\{{([^}}]+)\}}',
            content, re.DOTALL
        )
        if interface_match:
            prop_lines = interface_match.group(1).split('\n')
            for line in prop_lines:
                prop_match = re.match(r'\s*(\w+)', line)
                if prop_match:
                    props.append(prop_match.group(1))
        
        # Destructured props in function signature
        func_match = re.search(
            rf'(?:function|const)\s+{component_name}.*?\{{\s*([^}}]+)\s*\}}',
            content
        )
        if func_match:
            props.extend([p.strip() for p in func_match.group(1).split(',')])
        
        return list(set(props))
    
    def _extract_hooks(self, content: str) -> List[str]:
        """Extract React hooks used"""
        hooks = []
        hook_pattern = r'use[A-Z]\w*'
        found_hooks = re.findall(hook_pattern, content)
        return list(set(found_hooks))
    
    def _extract_lifecycle_methods(self, content: str) -> List[str]:
        """Extract React lifecycle methods"""
        lifecycle = []
        methods = [
            'componentDidMount', 'componentDidUpdate', 'componentWillUnmount',
            'shouldComponentUpdate', 'componentDidCatch', 'getDerivedStateFromProps'
        ]
        
        for method in methods:
            if method in content:
                lifecycle.append(method)
        
        return lifecycle
    
    def _infer_purpose(self, file_path: str, elements: List[JSCodeElement], 
                      components: List[Dict], api_calls: List[Dict], 
                      framework: str) -> str:
        """Infer the purpose of the file"""
        file_name = Path(file_path).stem
        
        if components:
            comp_names = ', '.join(c['name'] for c in components[:3])
            return f"React components: {comp_names}"
        elif api_calls and any(a['type'] == 'express_route' for a in api_calls):
            return f"API endpoints with {len(api_calls)} routes"
        elif 'test' in file_name or 'spec' in file_name:
            return "Test suite"
        elif 'config' in file_name:
            return "Configuration"
        elif 'utils' in file_name or 'helpers' in file_name:
            return "Utility functions"
        elif 'index' in file_name:
            return "Module entry point"
        elif framework != 'vanilla':
            return f"{framework.capitalize()} module"
        else:
            return f"JavaScript module with {len(elements)} elements"