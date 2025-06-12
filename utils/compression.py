import os
import zipfile
import tarfile
import gzip
import shutil
import threading
import time
from pathlib import Path
from typing import List, Optional, Callable, Dict, Union
import tempfile
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CompressionFormat(Enum):
    """Supported compression formats"""
    ZIP = "zip"
    TAR = "tar"
    TAR_GZ = "tar.gz"
    TAR_BZ2 = "tar.bz2"
    GZIP = "gzip"

@dataclass
class CompressionStats:
    """Statistics for compression operation"""
    original_size: int = 0
    compressed_size: int = 0
    files_processed: int = 0
    compression_ratio: float = 0.0
    time_elapsed: float = 0.0
    
    def calculate_ratio(self):
        """Calculate compression ratio"""
        if self.original_size > 0:
            self.compression_ratio = (1 - self.compressed_size / self.original_size) * 100
        else:
            self.compression_ratio = 0.0

class CompressionError(Exception):
    """Custom exception for compression operations"""
    pass

class CompressionManager:
    """Advanced compression and decompression manager with performance optimizations"""
    
    SUPPORTED_FORMATS = {
        '.zip': CompressionFormat.ZIP,
        '.tar': CompressionFormat.TAR,
        '.tar.gz': CompressionFormat.TAR_GZ,
        '.tgz': CompressionFormat.TAR_GZ,
        '.tar.bz2': CompressionFormat.TAR_BZ2,
        '.gz': CompressionFormat.GZIP
    }
    
    # Magic number signatures for format detection
    MAGIC_NUMBERS = {
        b'PK\x03\x04': CompressionFormat.ZIP,
        b'PK\x05\x06': CompressionFormat.ZIP,
        b'PK\x07\x08': CompressionFormat.ZIP,
        b'\x1f\x8b': CompressionFormat.GZIP,
        b'BZh': CompressionFormat.TAR_BZ2,
    }
    
    def __init__(self, chunk_size: int = 1024 * 1024, max_memory_usage: int = 100 * 1024 * 1024):
        """
        Initialize compression manager
        
        Args:
            chunk_size: Size of chunks for reading files (default 1MB)
            max_memory_usage: Maximum memory usage limit (default 100MB)
        """
        self.progress_callback: Optional[Callable] = None
        self.chunk_size = chunk_size
        self.max_memory_usage = max_memory_usage
        self._cancel_event = threading.Event()
        self._compression_lock = threading.Lock()
        
        # Statistics
        self.stats = CompressionStats()
        
    def set_progress_callback(self, callback: Callable[[float, int, int], None]):
        """
        Set callback for progress updates
        
        Args:
            callback: Function that receives (progress_percent, current, total)
        """
        self.progress_callback = callback
    
    def cancel_operation(self):
        """Cancel current compression/decompression operation"""
        self._cancel_event.set()
        logger.info("Compression operation cancellation requested")
    
    def compress_files(self, 
                      file_paths: List[str], 
                      output_path: str,
                      compression_format: Union[str, CompressionFormat] = CompressionFormat.ZIP,
                      compression_level: int = 6,
                      password: Optional[str] = None,
                      exclude_patterns: Optional[List[str]] = None) -> CompressionStats:
        """
        Compress files and directories with advanced options
        
        Args:
            file_paths: List of file/directory paths to compress
            output_path: Output archive path
            compression_format: Compression format to use
            compression_level: Compression level (0-9)
            password: Password for encryption (ZIP only)
            exclude_patterns: Patterns to exclude from compression
            
        Returns:
            CompressionStats: Statistics about the compression operation
            
        Raises:
            CompressionError: If compression fails
        """
        if not file_paths:
            raise CompressionError("No files specified for compression")
        
        # Validate inputs
        self._validate_compression_inputs(file_paths, output_path, compression_level)
        
        # Convert string format to enum
        if isinstance(compression_format, str):
            try:
                compression_format = CompressionFormat(compression_format.lower())
            except ValueError:
                raise CompressionError(f"Unsupported compression format: {compression_format}")
        
        with self._compression_lock:
            self._cancel_event.clear()
            self.stats = CompressionStats()
            start_time = time.time()
            
            try:
                logger.info(f"Starting compression to {output_path} with format {compression_format.value}")
                
                if compression_format == CompressionFormat.ZIP:
                    self._compress_zip(file_paths, output_path, compression_level, password, exclude_patterns)
                elif compression_format in [CompressionFormat.TAR, CompressionFormat.TAR_GZ, CompressionFormat.TAR_BZ2]:
                    self._compress_tar(file_paths, output_path, compression_format, exclude_patterns)
                elif compression_format == CompressionFormat.GZIP:
                    self._compress_gzip(file_paths, output_path, exclude_patterns)
                else:
                    raise CompressionError(f"Unsupported compression format: {compression_format}")
                
                # Calculate final statistics
                self.stats.time_elapsed = time.time() - start_time
                if os.path.exists(output_path):
                    self.stats.compressed_size = os.path.getsize(output_path)
                self.stats.calculate_ratio()
                
                logger.info(f"Compression completed in {self.stats.time_elapsed:.2f}s, "
                           f"ratio: {self.stats.compression_ratio:.1f}%")
                
                return self.stats
                
            except Exception as e:
                # Clean up partial file on error
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except:
                        pass
                
                logger.error(f"Compression failed: {e}")
                raise CompressionError(f"Compression operation failed: {e}")
    
    def _compress_zip(self, file_paths: List[str], output_path: str, 
                     level: int, password: Optional[str], exclude_patterns: Optional[List[str]]):
        """Compress files to ZIP format with memory optimization"""
        total_files = sum(1 for path in file_paths for _ in self._walk_path_with_exclusions(path, exclude_patterns))
        processed = 0
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=level) as zipf:
            # Set password if provided
            if password:
                zipf.setpassword(password.encode('utf-8'))
            
            for file_path in file_paths:
                if self._cancel_event.is_set():
                    raise CompressionError("Operation cancelled by user")
                
                if os.path.isfile(file_path):
                    self._add_file_to_zip(zipf, file_path, os.path.basename(file_path))
                    processed += 1
                    self._update_progress(processed, total_files)
                    
                elif os.path.isdir(file_path):
                    for file_full_path in self._walk_path_with_exclusions(file_path, exclude_patterns):
                        if self._cancel_event.is_set():
                            raise CompressionError("Operation cancelled by user")
                        
                        # Calculate relative path for archive
                        rel_path = os.path.relpath(file_full_path, os.path.dirname(file_path))
                        self._add_file_to_zip(zipf, file_full_path, rel_path)
                        processed += 1
                        self._update_progress(processed, total_files)
    
    def _add_file_to_zip(self, zipf: zipfile.ZipFile, file_path: str, arcname: str):
        """Add single file to ZIP with memory management"""
        try:
            file_size = os.path.getsize(file_path)
            self.stats.original_size += file_size
            self.stats.files_processed += 1
            
            # For large files, use streaming approach
            if file_size > self.max_memory_usage:
                self._add_large_file_to_zip(zipf, file_path, arcname)
            else:
                zipf.write(file_path, arcname)
                
        except (OSError, PermissionError) as e:
            logger.warning(f"Cannot add file {file_path} to archive: {e}")
    
    def _add_large_file_to_zip(self, zipf: zipfile.ZipFile, file_path: str, arcname: str):
        """Add large file to ZIP using streaming to avoid memory issues"""
        with open(file_path, 'rb') as src:
            with zipf.open(arcname, 'w') as dest:
                while True:
                    chunk = src.read(self.chunk_size)
                    if not chunk:
                        break
                    dest.write(chunk)
    
    def _compress_tar(self, file_paths: List[str], output_path: str, 
                     comp_format: CompressionFormat, exclude_patterns: Optional[List[str]]):
        """Compress files to TAR format"""
        mode_map = {
            CompressionFormat.TAR: 'w',
            CompressionFormat.TAR_GZ: 'w:gz',
            CompressionFormat.TAR_BZ2: 'w:bz2'
        }
        
        total_files = sum(1 for path in file_paths for _ in self._walk_path_with_exclusions(path, exclude_patterns))
        processed = 0
        
        with tarfile.open(output_path, mode_map[comp_format]) as tar:
            for file_path in file_paths:
                if self._cancel_event.is_set():
                    raise CompressionError("Operation cancelled by user")
                
                if os.path.isfile(file_path):
                    arcname = os.path.basename(file_path)
                    self._add_file_to_tar(tar, file_path, arcname)
                    processed += 1
                    self._update_progress(processed, total_files)
                    
                elif os.path.isdir(file_path):
                    for file_full_path in self._walk_path_with_exclusions(file_path, exclude_patterns):
                        if self._cancel_event.is_set():
                            raise CompressionError("Operation cancelled by user")
                        
                        rel_path = os.path.relpath(file_full_path, os.path.dirname(file_path))
                        self._add_file_to_tar(tar, file_full_path, rel_path)
                        processed += 1
                        self._update_progress(processed, total_files)
    
    def _add_file_to_tar(self, tar: tarfile.TarFile, file_path: str, arcname: str):
        """Add single file to TAR archive"""
        try:
            file_size = os.path.getsize(file_path)
            self.stats.original_size += file_size
            self.stats.files_processed += 1
            tar.add(file_path, arcname=arcname)
        except (OSError, PermissionError) as e:
            logger.warning(f"Cannot add file {file_path} to archive: {e}")
    
    def _compress_gzip(self, file_paths: List[str], output_path: str, exclude_patterns: Optional[List[str]]):
        """Compress single file to GZIP (GZIP only supports single file)"""
        if len(file_paths) != 1:
            raise CompressionError("GZIP format only supports single file compression")
        
        file_path = file_paths[0]
        if not os.path.isfile(file_path):
            raise CompressionError("GZIP compression requires a single file")
        
        file_size = os.path.getsize(file_path)
        self.stats.original_size = file_size
        self.stats.files_processed = 1
        
        with open(file_path, 'rb') as f_in:
            with gzip.open(output_path, 'wb') as f_out:
                processed = 0
                while True:
                    if self._cancel_event.is_set():
                        raise CompressionError("Operation cancelled by user")
                    
                    chunk = f_in.read(self.chunk_size)
                    if not chunk:
                        break
                    
                    f_out.write(chunk)
                    processed += len(chunk)
                    self._update_progress(processed, file_size)
    
    def extract_archive(self, 
                       archive_path: str, 
                       extract_to: str,
                       password: Optional[str] = None,
                       overwrite: bool = False,
                       extract_filter: Optional[Callable[[str], bool]] = None) -> CompressionStats:
        """
        Extract archive with advanced options
        
        Args:
            archive_path: Path to archive file
            extract_to: Directory to extract to
            password: Password for encrypted archives
            overwrite: Whether to overwrite existing files
            extract_filter: Function to filter which files to extract
            
        Returns:
            CompressionStats: Statistics about the extraction operation
        """
        if not os.path.exists(archive_path):
            raise CompressionError(f"Archive file not found: {archive_path}")
        
        if not os.path.isfile(archive_path):
            raise CompressionError(f"Path is not a file: {archive_path}")
        
        # Create extraction directory if it doesn't exist
        os.makedirs(extract_to, exist_ok=True)
        
        with self._compression_lock:
            self._cancel_event.clear()
            self.stats = CompressionStats()
            start_time = time.time()
            
            try:
                archive_format = self._detect_archive_format(archive_path)
                logger.info(f"Extracting {archive_format.value} archive: {archive_path}")
                
                if archive_format == CompressionFormat.ZIP:
                    self._extract_zip(archive_path, extract_to, password, overwrite, extract_filter)
                elif archive_format in [CompressionFormat.TAR, CompressionFormat.TAR_GZ, CompressionFormat.TAR_BZ2]:
                    self._extract_tar(archive_path, extract_to, archive_format, overwrite, extract_filter)
                elif archive_format == CompressionFormat.GZIP:
                    self._extract_gzip(archive_path, extract_to, overwrite)
                else:
                    raise CompressionError(f"Unsupported archive format: {archive_format}")
                
                # Calculate statistics
                self.stats.time_elapsed = time.time() - start_time
                self.stats.compressed_size = os.path.getsize(archive_path)
                
                logger.info(f"Extraction completed in {self.stats.time_elapsed:.2f}s, "
                           f"extracted {self.stats.files_processed} files")
                
                return self.stats
                
            except Exception as e:
                logger.error(f"Extraction failed: {e}")
                raise CompressionError(f"Extraction operation failed: {e}")
    
    def _extract_zip(self, archive_path: str, extract_to: str, password: Optional[str], 
                    overwrite: bool, extract_filter: Optional[Callable]):
        """Extract ZIP archive with security checks"""
        try:
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                members = zipf.namelist()
                total_files = len(members)
                
                for i, member in enumerate(members):
                    if self._cancel_event.is_set():
                        raise CompressionError("Operation cancelled by user")
                    
                    # Apply filter if provided
                    if extract_filter and not extract_filter(member):
                        continue
                    
                    # Security check for path traversal
                    if not self._is_safe_extract_path(extract_to, member):
                        logger.warning(f"Skipping unsafe path: {member}")
                        continue
                    
                    # Check if file exists and overwrite flag
                    full_path = os.path.join(extract_to, member)
                    if os.path.exists(full_path) and not overwrite:
                        logger.info(f"Skipping existing file: {member}")
                        continue
                    
                    try:
                        if password:
                            zipf.extract(member, extract_to, pwd=password.encode('utf-8'))
                        else:
                            zipf.extract(member, extract_to)
                        
                        self.stats.files_processed += 1
                        if os.path.exists(full_path):
                            self.stats.original_size += os.path.getsize(full_path)
                            
                    except RuntimeError as e:
                        if "Bad password" in str(e):
                            raise CompressionError("Invalid password for encrypted archive")
                        else:
                            logger.warning(f"Failed to extract {member}: {e}")
                    
                    self._update_progress(i + 1, total_files)
                    
        except zipfile.BadZipFile:
            raise CompressionError("Invalid or corrupted ZIP file")
    
    def _extract_tar(self, archive_path: str, extract_to: str, archive_format: CompressionFormat,
                    overwrite: bool, extract_filter: Optional[Callable]):
        """Extract TAR archive"""
        mode_map = {
            CompressionFormat.TAR: 'r',
            CompressionFormat.TAR_GZ: 'r:gz',
            CompressionFormat.TAR_BZ2: 'r:bz2'
        }
        
        try:
            with tarfile.open(archive_path, mode_map[archive_format]) as tar:
                members = tar.getmembers()
                total_files = len(members)
                
                for i, member in enumerate(members):
                    if self._cancel_event.is_set():
                        raise CompressionError("Operation cancelled by user")
                    
                    # Apply filter if provided
                    if extract_filter and not extract_filter(member.name):
                        continue
                    
                    # Security check
                    if not self._is_safe_extract_path(extract_to, member.name):
                        logger.warning(f"Skipping unsafe path: {member.name}")
                        continue
                    
                    # Check overwrite
                    full_path = os.path.join(extract_to, member.name)
                    if os.path.exists(full_path) and not overwrite:
                        logger.info(f"Skipping existing file: {member.name}")
                        continue
                    
                    try:
                        tar.extract(member, extract_to)
                        self.stats.files_processed += 1
                        if member.isfile():
                            self.stats.original_size += member.size
                    except Exception as e:
                        logger.warning(f"Failed to extract {member.name}: {e}")
                    
                    self._update_progress(i + 1, total_files)
                    
        except tarfile.TarError as e:
            raise CompressionError(f"Invalid or corrupted TAR file: {e}")
    
    def _extract_gzip(self, archive_path: str, extract_to: str, overwrite: bool):
        """Extract GZIP file"""
        output_filename = os.path.splitext(os.path.basename(archive_path))[0]
        output_path = os.path.join(extract_to, output_filename)
        
        if os.path.exists(output_path) and not overwrite:
            raise CompressionError(f"Output file already exists: {output_path}")
        
        try:
            with gzip.open(archive_path, 'rb') as f_in:
                with open(output_path, 'wb') as f_out:
                    processed = 0
                    while True:
                        if self._cancel_event.is_set():
                            raise CompressionError("Operation cancelled by user")
                        
                        chunk = f_in.read(self.chunk_size)
                        if not chunk:
                            break
                        
                        f_out.write(chunk)
                        processed += len(chunk)
                        self.stats.original_size = processed
                        self._update_progress(processed, processed)  # Can't know total size beforehand
            
            self.stats.files_processed = 1
            
        except gzip.BadGzipFile:
            raise CompressionError("Invalid or corrupted GZIP file")
    
    def _detect_archive_format(self, file_path: str) -> CompressionFormat:
        """Detect archive format using extension and magic numbers"""
        path = Path(file_path)
        
        # Check extension first
        if path.suffixes:
            # Handle double extensions like .tar.gz
            if len(path.suffixes) >= 2:
                double_ext = ''.join(path.suffixes[-2:])
                if double_ext in self.SUPPORTED_FORMATS:
                    return self.SUPPORTED_FORMATS[double_ext]
            
            # Single extension
            if path.suffix in self.SUPPORTED_FORMATS:
                return self.SUPPORTED_FORMATS[path.suffix]
        
        # Fallback to magic number detection
        try:
            with open(file_path, 'rb') as f:
                header = f.read(10)
                for magic, format_type in self.MAGIC_NUMBERS.items():
                    if header.startswith(magic):
                        return format_type
                
                # Check for TAR signature at offset 257
                f.seek(257)
                tar_signature = f.read(5)
                if tar_signature == b'ustar':
                    return CompressionFormat.TAR
                    
        except Exception as e:
            logger.warning(f"Could not read file header: {e}")
        
        raise CompressionError(f"Unknown or unsupported archive format: {file_path}")
    
    def _is_safe_extract_path(self, extract_to: str, member_path: str) -> bool:
        """Security check to prevent path traversal attacks"""
        extract_to = os.path.abspath(extract_to)
        member_path = os.path.abspath(os.path.join(extract_to, member_path))
        return member_path.startswith(extract_to)
    
    def _walk_path_with_exclusions(self, path: str, exclude_patterns: Optional[List[str]]):
        """Generator to walk path with exclusion patterns"""
        if os.path.isfile(path):
            if not self._is_excluded(path, exclude_patterns):
                yield path
        else:
            for root, dirs, files in os.walk(path):
                # Filter directories
                dirs[:] = [d for d in dirs if not self._is_excluded(os.path.join(root, d), exclude_patterns)]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    if not self._is_excluded(file_path, exclude_patterns):
                        yield file_path
    
    def _is_excluded(self, file_path: str, exclude_patterns: Optional[List[str]]) -> bool:
        """Check if file should be excluded based on patterns"""
        if not exclude_patterns:
            return False
        
        import fnmatch
        filename = os.path.basename(file_path)
        
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(file_path, pattern):
                return True
        
        return False
    
    def _update_progress(self, current: int, total: int):
        """Update progress callback"""
        if self.progress_callback:
            progress = (current / total) * 100 if total > 0 else 0
            self.progress_callback(progress, current, total)
    
    def _validate_compression_inputs(self, file_paths: List[str], output_path: str, compression_level: int):
        """Validate compression parameters"""
        # Check if all input files exist
        for file_path in file_paths:
            if not os.path.exists(file_path):
                raise CompressionError(f"Input file/directory not found: {file_path}")
        
        # Check output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            raise CompressionError(f"Output directory does not exist: {output_dir}")
        
        # Check if output file already exists
        if os.path.exists(output_path):
            raise CompressionError(f"Output file already exists: {output_path}")
        
        # Validate compression level
        if not 0 <= compression_level <= 9:
            raise CompressionError(f"Invalid compression level: {compression_level} (must be 0-9)")
    
    def get_archive_info(self, archive_path: str) -> Dict:
        """Get detailed information about archive"""
        try:
            if not os.path.exists(archive_path):
                raise CompressionError(f"Archive file not found: {archive_path}")
            
            archive_format = self._detect_archive_format(archive_path)
            file_stat = os.stat(archive_path)
            
            info = {
                'format': archive_format.value,
                'size': file_stat.st_size,
                'size_formatted': self._format_size(file_stat.st_size),
                'modified': datetime.fromtimestamp(file_stat.st_mtime),
                'files': [],
                'file_count': 0,
                'is_encrypted': False
            }
            
            if archive_format == CompressionFormat.ZIP:
                with zipfile.ZipFile(archive_path, 'r') as zipf:
                    info['files'] = zipf.namelist()
                    info['file_count'] = len(info['files'])
                    # Check if encrypted
                    for file_info in zipf.filelist:
                        if file_info.flag_bits & 0x1:
                            info['is_encrypted'] = True
                            break
                            
            elif archive_format in [CompressionFormat.TAR, CompressionFormat.TAR_GZ, CompressionFormat.TAR_BZ2]:
                mode_map = {
                    CompressionFormat.TAR: 'r',
                    CompressionFormat.TAR_GZ: 'r:gz',
                    CompressionFormat.TAR_BZ2: 'r:bz2'
                }
                with tarfile.open(archive_path, mode_map[archive_format]) as tar:
                    info['files'] = tar.getnames()
                    info['file_count'] = len(info['files'])
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get archive info: {e}")
            return {'error': str(e)}
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported compression formats"""
        return [fmt.value for fmt in CompressionFormat]
    
    def estimate_compression_size(self, file_paths: List[str], compression_format: CompressionFormat) -> int:
        """Estimate compressed size (rough approximation)"""
        total_size = 0
        for file_path in file_paths:
            if os.path.isfile(file_path):
                total_size += os.path.getsize(file_path)
            else:
                for root, dirs, files in os.walk(file_path):
                    for file in files:
                        try:
                            total_size += os.path.getsize(os.path.join(root, file))
                        except OSError:
                            continue
        
        # Rough compression ratios
        compression_ratios = {
            CompressionFormat.ZIP: 0.7,
            CompressionFormat.TAR: 1.0,
            CompressionFormat.TAR_GZ: 0.3,
            CompressionFormat.TAR_BZ2: 0.25,
            CompressionFormat.GZIP: 0.3
        }
        
        return int(total_size * compression_ratios.get(compression_format, 0.7))