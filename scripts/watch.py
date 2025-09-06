#!/usr/bin/env python3
"""
File watcher for continuous documentation updates
Monitors Python files and updates documentation automatically
"""

import sys
import time
import logging
from pathlib import Path
from typing import List
import click
from colorama import init, Fore, Style
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from autodoc.core import DocumentationSystem

# Initialize colorama
init()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class DocumentationWatcher(FileSystemEventHandler):
    """Watches for file changes and updates documentation"""
    
    def __init__(self, doc_system: DocumentationSystem):
        self.doc_system = doc_system
        self.pending_files = {}
        self.last_event_time = {}
        self.debounce_seconds = 2
    
    def should_process(self, file_path: str) -> bool:
        """Check if file should be processed with debouncing"""
        current_time = time.time()
        last_time = self.last_event_time.get(file_path, 0)
        
        # Debounce: wait specified seconds after last event
        if current_time - last_time < self.debounce_seconds:
            self.pending_files[file_path] = current_time
            return False
        
        self.last_event_time[file_path] = current_time
        return True
    
    def process_pending(self):
        """Process any pending files that have settled"""
        current_time = time.time()
        files_to_process = []
        
        for file_path, event_time in list(self.pending_files.items()):
            if current_time - event_time >= self.debounce_seconds:
                files_to_process.append(file_path)
                del self.pending_files[file_path]
        
        for file_path in files_to_process:
            self._process_file(file_path)
    
    def _process_file(self, file_path: str):
        """Process a single file"""
        if not Path(file_path).exists():
            logger.info(f"{Fore.YELLOW}⚠️ File deleted: {file_path}{Style.RESET_ALL}")
            return
        
        if not file_path.endswith('.py'):
            return
        
        # Check if it should be processed
        if not self.doc_system.should_process_file(file_path):
            return
        
        logger.info(f"{Fore.CYAN}📝 Processing: {file_path}{Style.RESET_ALL}")
        
        try:
            analysis = self.doc_system.process_file(file_path)
            if analysis:
                logger.info(f"{Fore.GREEN}✅ Updated: {file_path}{Style.RESET_ALL}")
                
                # Show summary
                logger.info(f"   Found: {len(analysis.elements)} elements, "
                          f"{len(analysis.api_routes)} routes, "
                          f"{len(analysis.database_models)} models")
            else:
                logger.info(f"{Fore.YELLOW}⏭️ Skipped: {file_path} (unchanged){Style.RESET_ALL}")
                
        except Exception as e:
            logger.error(f"{Fore.RED}❌ Error processing {file_path}: {e}{Style.RESET_ALL}")
    
    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        # Only process Python files
        if not file_path.endswith('.py'):
            return
        
        # Check ignored patterns
        if any(pattern in file_path for pattern in self.doc_system.ignored_patterns):
            return
        
        if self.should_process(file_path):
            self._process_file(file_path)
    
    def on_created(self, event):
        """Handle file creation events"""
        self.on_modified(event)
    
    def on_deleted(self, event):
        """Handle file deletion events"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        # Only process Python files
        if not file_path.endswith('.py'):
            return
        
        # Check ignored patterns
        if any(pattern in file_path for pattern in self.doc_system.ignored_patterns):
            return
        
        logger.info(f"{Fore.RED}🗑️ File deleted: {file_path}{Style.RESET_ALL}")
        
        try:
            # Remove from documentation system
            self.doc_system.remove_file(file_path)
            logger.info(f"{Fore.GREEN}✅ Removed from index: {file_path}{Style.RESET_ALL}")
        except Exception as e:
            logger.error(f"{Fore.RED}❌ Error removing {file_path}: {e}{Style.RESET_ALL}")


class WatcherManager:
    """Manages the file watching process"""
    
    def __init__(self, doc_system: DocumentationSystem):
        self.doc_system = doc_system
        self.observer = Observer()
        self.handler = DocumentationWatcher(doc_system)
        self.watching_dirs = []
    
    def add_directory(self, directory: str):
        """Add a directory to watch"""
        dir_path = Path(directory).resolve()
        
        if not dir_path.exists():
            logger.warning(f"{Fore.YELLOW}Directory not found: {directory}{Style.RESET_ALL}")
            return False
        
        self.observer.schedule(self.handler, str(dir_path), recursive=True)
        self.watching_dirs.append(str(dir_path))
        logger.info(f"{Fore.GREEN}👁️ Watching: {dir_path}{Style.RESET_ALL}")
        return True
    
    def start(self):
        """Start the file watcher"""
        if not self.watching_dirs:
            logger.error(f"{Fore.RED}No directories to watch!{Style.RESET_ALL}")
            return
        
        self.observer.start()
        
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}📡 File Watcher Active{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"Watching {len(self.watching_dirs)} directories")
        print(f"Press {Fore.YELLOW}Ctrl+C{Style.RESET_ALL} to stop\n")
        
        try:
            while True:
                time.sleep(1)
                # Process any pending files
                self.handler.process_pending()
                
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Stopping file watcher...{Style.RESET_ALL}")
            self.observer.stop()
        
        self.observer.join()
        print(f"{Fore.GREEN}File watcher stopped.{Style.RESET_ALL}")


@click.command()
@click.option('--project-root', default='.', help='Project root directory')
@click.option('--docs-dir', default='docs', help='Documentation directory')
@click.option('--directories', '-d', multiple=True, default=['src', 'app'], help='Directories to watch')
@click.option('--debounce', default=2, help='Debounce time in seconds')
@click.option('--scan-first', is_flag=True, help='Scan all files before watching')
def main(project_root, docs_dir, directories, debounce, scan_first):
    """Watch Python files and update documentation automatically"""
    
    print(f"\n{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🔍 Documentation File Watcher{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}\n")
    
    # Initialize documentation system
    doc_system = DocumentationSystem(
        project_root=project_root,
        docs_dir=docs_dir
    )
    
    # Scan first if requested
    if scan_first:
        print(f"{Fore.YELLOW}📊 Running initial scan...{Style.RESET_ALL}")
        doc_system.process_project(list(directories), parallel=True)
        print(f"{Fore.GREEN}✅ Initial scan complete{Style.RESET_ALL}\n")
    
    # Create watcher
    watcher = WatcherManager(doc_system)
    watcher.handler.debounce_seconds = debounce
    
    # Add directories
    added_any = False
    for directory in directories:
        if watcher.add_directory(directory):
            added_any = True
    
    # Also watch the project root if no specific directories
    if not directories or not added_any:
        watcher.add_directory(project_root)
    
    # Start watching
    watcher.start()


if __name__ == "__main__":
    main()