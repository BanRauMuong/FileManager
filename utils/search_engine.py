import os
import re
import fnmatch
import threading
import time
from pathlib import Path
from typing import List, Dict, Optional, Callable, Generator
from datetime import datetime, timedelta
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Data class for search results"""
    path: str
    name: str
    size: int
    modified: datetime
    directory: str
    match_type: str = "filename"  # filename, content, both
    match_line: Optional[str] = None
    match_line_number: Optional[int] = None

class SearchError(Exception):
    """Custom exception for search operations"""
    pass

class SearchIndex:
    """Simple file index for faster searches"""
    
    def __init__(self):
        self.index = {}  # {word: [file_paths]}
        self.file_timestamps = {}  # {file_path: timestamp}
        self.lock = threading.RLock()
    
    def is_indexed(self, file_path: str) -> bool:
        """Check if file is in index and up to date"""
        with self.lock:
            if file_path not in self.file_timestamps:
                return False
            
            try:
                current_mtime = os.path.getmtime(file_path)
                return self.file_timestamps[file_path] >= current_mtime
            except OSError:
                return False
    
    def add_file(self, file_path: str):
        """Add file to index"""
        try:
            with self.lock:
                filename = os.path.basename(file_path).lower()
                words = re.findall(r'\w+', filename)
                
                for word in words:
                    if word not in self.index:
                        self.index[word] = set()
                    self.index[word].add(file_path)
                
                self.file_timestamps[file_path] = os.path.getmtime(file_path)
        except Exception as e:
            logger.warning(f"Failed to index file {file_path}: {e}")
    
    def search(self, query: str) -> set:
        """Search in index"""
        with self.lock:
            query_words = re.findall(r'\w+', query.lower())
            if not query_words:
                return set()
            
            result_sets = []
            for word in query_words:
                matches = set()
                for indexed_word in self.index:
                    if word in indexed_word:
                        matches.update(self.index[indexed_word])
                result_sets.append(matches)
            
            # Return intersection of all word matches
            if result_sets:
                return set.intersection(*result_sets)
            return set()

class SearchEngine:
    """Advanced file search engine with performance optimizations"""
    
    def __init__(self, max_workers: int = 4):
        self.search_history = []
        self.max_history = 50
        self._cancel_event = threading.Event()
        self._search_lock = threading.Lock()
        self.index = SearchIndex()
        self.max_workers = max_workers
        
        # Configuration
        self.chunk_size = 8192  # For reading file content
        self.max_file_size_for_content_search = 10 * 1024 * 1024  # 10MB
        self.indexing_enabled = True
    
    def cancel_search(self):
        """Cancel current search operation"""
        self._cancel_event.set()
        logger.info("Search cancellation requested")
    
    def search_files(self, 
                    root_path: str,
                    pattern: str = "*",
                    content_search: str = None,
                    file_type: str = None,
                    size_min: int = None,
                    size_max: int = None,
                    date_from: datetime = None,
                    date_to: datetime = None,
                    case_sensitive: bool = False,
                    regex: bool = False,
                    max_results: int = 1000,
                    use_index: bool = True,
                    progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        """
        Advanced file search with multiple criteria and performance optimizations
        """
        if not os.path.exists(root_path):
            raise SearchError(f"Root path does not exist: {root_path}")
        
        if not os.path.isdir(root_path):
            raise SearchError(f"Root path is not a directory: {root_path}")
        
        with self._search_lock:
            self._cancel_event.clear()
            start_time = time.time()
            
            # Add to search history
            self._add_to_history({
                'pattern': pattern,
                'content_search': content_search,
                'timestamp': datetime.now(),
                'root_path': root_path,
                'file_type': file_type
            })
            
            try:
                if use_index and self.indexing_enabled and not content_search:
                    # Use index for filename-only searches
                    results = self._search_with_index(
                        root_path, pattern, file_type, size_min, size_max,
                        date_from, date_to, case_sensitive, regex, max_results, progress_callback
                    )
                else:
                    # Full filesystem search
                    results = self._search_filesystem(
                        root_path, pattern, content_search, file_type, size_min, size_max,
                        date_from, date_to, case_sensitive, regex, max_results, progress_callback
                    )
                
                search_time = time.time() - start_time
                logger.info(f"Search completed in {search_time:.2f}s, found {len(results)} results")
                return results
                
            except Exception as e:
                logger.error(f"Search failed: {e}")
                raise SearchError(f"Search operation failed: {e}")
    
    def _search_with_index(self, root_path: str, pattern: str, file_type: str,
                          size_min: int, size_max: int, date_from: datetime,
                          date_to: datetime, case_sensitive: bool, regex: bool,
                          max_results: int, progress_callback: Optional[Callable]) -> List[SearchResult]:
        """Search using index for better performance"""
        # Build/update index if needed
        self._update_index(root_path, progress_callback)
        
        if self._cancel_event.is_set():
            return []
        
        # Search in index
        candidate_files = self.index.search(pattern)
        results = []
        
        for i, file_path in enumerate(candidate_files):
            if self._cancel_event.is_set() or len(results) >= max_results:
                break
            
            if self._matches_criteria(file_path, pattern, file_type, size_min, size_max,
                                    date_from, date_to, case_sensitive, regex):
                try:
                    stat = os.stat(file_path)
                    results.append(SearchResult(
                        path=file_path,
                        name=os.path.basename(file_path),
                        size=stat.st_size,
                        modified=datetime.fromtimestamp(stat.st_mtime),
                        directory=os.path.dirname(file_path),
                        match_type="filename"
                    ))
                except OSError:
                    continue
            
            if progress_callback and i % 100 == 0:
                progress_callback(i, len(candidate_files))
        
        return results
    
    def _search_filesystem(self, root_path: str, pattern: str, content_search: str,
                          file_type: str, size_min: int, size_max: int,
                          date_from: datetime, date_to: datetime, case_sensitive: bool,
                          regex: bool, max_results: int, progress_callback: Optional[Callable]) -> List[SearchResult]:
        """Full filesystem search with content search support"""
        results = []
        search_count = 0
        total_files = self._estimate_file_count(root_path) if progress_callback else 0
        
        try:
            for root, dirs, files in os.walk(root_path):
                if self._cancel_event.is_set():
                    break
                
                # Filter hidden directories if needed
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file in files:
                    if self._cancel_event.is_set() or len(results) >= max_results:
                        break
                    
                    file_path = os.path.join(root, file)
                    search_count += 1
                    
                    # Update progress
                    if progress_callback and search_count % 50 == 0:
                        progress_callback(search_count, total_files)
                    
                    try:
                        if self._process_file(file_path, pattern, content_search, file_type,
                                            size_min, size_max, date_from, date_to,
                                            case_sensitive, regex, results):
                            # Add to index for future searches
                            if self.indexing_enabled:
                                self.index.add_file(file_path)
                    
                    except (OSError, PermissionError) as e:
                        logger.debug(f"Cannot access file {file_path}: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Filesystem search error: {e}")
            raise SearchError(f"Filesystem search failed: {e}")
        
        return results
    
    def _process_file(self, file_path: str, pattern: str, content_search: str,
                     file_type: str, size_min: int, size_max: int,
                     date_from: datetime, date_to: datetime, case_sensitive: bool,
                     regex: bool, results: List[SearchResult]) -> bool:
        """Process a single file for search criteria"""
        filename = os.path.basename(file_path)
        
        # Check filename pattern
        if not self._match_pattern(filename, pattern, case_sensitive, regex):
            return False
        
        # Check file type
        if file_type and not filename.lower().endswith(file_type.lower()):
            return False
        
        stat = os.stat(file_path)
        
        # Check size constraints
        if size_min and stat.st_size < size_min:
            return False
        if size_max and stat.st_size > size_max:
            return False
        
        # Check date constraints
        file_date = datetime.fromtimestamp(stat.st_mtime)
        if date_from and file_date < date_from:
            return False
        if date_to and file_date > date_to:
            return False
        
        # Content search
        content_match = None
        content_line_num = None
        match_type = "filename"
        
        if content_search:
            if stat.st_size > self.max_file_size_for_content_search:
                logger.debug(f"Skipping content search for large file: {file_path}")
            else:
                content_match, content_line_num = self._search_in_file_optimized(
                    file_path, content_search, case_sensitive
                )
                if content_match:
                    match_type = "content"
                elif not self._match_pattern(filename, content_search, case_sensitive, regex):
                    return False
        
        # Add to results
        results.append(SearchResult(
            path=file_path,
            name=filename,
            size=stat.st_size,
            modified=file_date,
            directory=os.path.dirname(file_path),
            match_type=match_type,
            match_line=content_match,
            match_line_number=content_line_num
        ))
        
        return True
    
    def _search_in_file_optimized(self, file_path: str, search_text: str, 
                                 case_sensitive: bool) -> tuple[Optional[str], Optional[int]]:
        """Memory-efficient content search with line tracking"""
        if not self._is_text_file(file_path):
            return None, None
        
        try:
            if not case_sensitive:
                search_text = search_text.lower()
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                line_num = 0
                buffer = ""
                
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    
                    buffer += chunk
                    lines = buffer.split('\n')
                    buffer = lines[-1]  # Keep incomplete line
                    
                    for line in lines[:-1]:
                        line_num += 1
                        search_line = line.lower() if not case_sensitive else line
                        
                        if search_text in search_line:
                            return line.strip()[:200], line_num  # Return first 200 chars
                
                # Check last line
                if buffer:
                    line_num += 1
                    search_line = buffer.lower() if not case_sensitive else buffer
                    if search_text in search_line:
                        return buffer.strip()[:200], line_num
            
            return None, None
            
        except Exception as e:
            logger.debug(f"Content search failed for {file_path}: {e}")
            return None, None
    
    def _is_text_file(self, file_path: str) -> bool:
        """Enhanced text file detection"""
        # Check extension first
        text_extensions = {
            '.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.md', '.csv',
            '.log', '.ini', '.cfg', '.conf', '.yaml', '.yml', '.sql', '.sh', '.bat',
            '.c', '.cpp', '.h', '.java', '.php', '.rb', '.go', '.rs', '.kt', '.swift'
        }
        
        if Path(file_path).suffix.lower() in text_extensions:
            return True
        
        # Check content for binary data
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                if not chunk:
                    return True
                
                # Check for null bytes (common in binary files)
                if b'\0' in chunk:
                    return False
                
                # Check ratio of printable characters
                printable_count = sum(1 for b in chunk if 32 <= b <= 126 or b in [9, 10, 13])
                return (printable_count / len(chunk)) > 0.7
        except:
            return False
    
    def _match_pattern(self, filename: str, pattern: str, case_sensitive: bool, regex: bool) -> bool:
        """Enhanced pattern matching"""
        if not case_sensitive:
            filename = filename.lower()
            pattern = pattern.lower()
        
        if regex:
            try:
                return bool(re.search(pattern, filename))
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")
                return False
        else:
            return fnmatch.fnmatch(filename, pattern)
    
    def _matches_criteria(self, file_path: str, pattern: str, file_type: str,
                         size_min: int, size_max: int, date_from: datetime,
                         date_to: datetime, case_sensitive: bool, regex: bool) -> bool:
        """Check if file matches all criteria"""
        try:
            filename = os.path.basename(file_path)
            
            # Pattern check
            if not self._match_pattern(filename, pattern, case_sensitive, regex):
                return False
            
            # File type check
            if file_type and not filename.lower().endswith(file_type.lower()):
                return False
            
            stat = os.stat(file_path)
            
            # Size checks
            if size_min and stat.st_size < size_min:
                return False
            if size_max and stat.st_size > size_max:
                return False
            
            # Date checks
            file_date = datetime.fromtimestamp(stat.st_mtime)
            if date_from and file_date < date_from:
                return False
            if date_to and file_date > date_to:
                return False
            
            return True
        except OSError:
            return False
    
    def _update_index(self, root_path: str, progress_callback: Optional[Callable]):
        """Update search index for the given path"""
        if not self.indexing_enabled:
            return
        
        files_to_index = []
        total_files = 0
        
        # Find files that need indexing
        for root, dirs, files in os.walk(root_path):
            if self._cancel_event.is_set():
                return
            
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                file_path = os.path.join(root, file)
                total_files += 1
                
                if not self.index.is_indexed(file_path):
                    files_to_index.append(file_path)
        
        # Index files
        for i, file_path in enumerate(files_to_index):
            if self._cancel_event.is_set():
                return
            
            self.index.add_file(file_path)
            
            if progress_callback and i % 100 == 0:
                progress_callback(i, len(files_to_index))
    
    def _estimate_file_count(self, root_path: str) -> int:
        """Estimate total number of files for progress tracking"""
        try:
            count = 0
            for root, dirs, files in os.walk(root_path):
                if self._cancel_event.is_set():
                    break
                count += len(files)
                if count > 10000:  # Cap estimation for performance
                    break
            return count
        except:
            return 1000  # Default estimate
    
    def _add_to_history(self, search_info: Dict):
        """Add search to history"""
        self.search_history.append(search_info)
        if len(self.search_history) > self.max_history:
            self.search_history.pop(0)
    
    def get_search_history(self) -> List[Dict]:
        """Get search history"""
        return self.search_history.copy()
    
    def clear_history(self):
        """Clear search history"""
        self.search_history.clear()
    
    def clear_index(self):
        """Clear search index"""
        self.index = SearchIndex()
    
    def quick_search(self, root_path: str, query: str, max_results: int = 100) -> List[str]:
        """Quick filename-only search"""
        if not os.path.exists(root_path):
            raise SearchError(f"Root path does not exist: {root_path}")
        
        results = []
        query_lower = query.lower()
        
        # Use index if available
        if self.indexing_enabled:
            indexed_results = self.index.search(query)
            return list(indexed_results)[:max_results]
        
        # Fallback to filesystem search
        try:
            for root, dirs, files in os.walk(root_path):
                if self._cancel_event.is_set() or len(results) >= max_results:
                    break
                
                for item in dirs + files:
                    if query_lower in item.lower():
                        results.append(os.path.join(root, item))
                        if len(results) >= max_results:
                            break
        except Exception as e:
            logger.error(f"Quick search failed: {e}")
            raise SearchError(f"Quick search failed: {e}")
        
        return results
    
    def get_stats(self) -> Dict:
        """Get search engine statistics"""
        return {
            'indexed_files': len(self.index.file_timestamps),
            'search_history_count': len(self.search_history),
            'indexing_enabled': self.indexing_enabled,
            'max_workers': self.max_workers,
            'chunk_size': self.chunk_size,
            'max_file_size_for_content_search': self.max_file_size_for_content_search
        }