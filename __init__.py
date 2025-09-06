"""
AutoDoc - Intelligent Documentation System
A portable documentation system with semantic search for preventing code redundancy
"""

__version__ = "1.0.0"
__author__ = "AutoDoc Team"

from .core.doc_system import (
    DocumentationSystem,
    CodeAnalyzer,
    LLMAnalyzer,
    SemanticIndexer,
    CodeElement,
    FileAnalysis
)

__all__ = [
    'DocumentationSystem',
    'CodeAnalyzer', 
    'LLMAnalyzer',
    'SemanticIndexer',
    'CodeElement',
    'FileAnalysis'
]